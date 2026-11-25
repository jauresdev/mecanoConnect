from collections.abc import Mapping
from datetime import timedelta
import mimetypes

from django.db import transaction
from django.db.models import Avg, Count, Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import (
    decorators,
    permissions,
    response,
    serializers,
    status,
    viewsets,
)
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import User

from .models import (
    Appointment,
    CustomerVehicle,
    Notification,
    QuoteMessage,
    QuoteOffer,
    QuoteReport,
    QuoteRequest,
    RepairShop,
    Review,
    Service,
    VehicleType,
)
from .permissions import IsShopOwnerOrReadOnly
from .serializers import (
    AppointmentSerializer,
    CustomerVehicleSerializer,
    NotificationSerializer,
    QuoteOfferSerializer,
    QuoteReportSerializer,
    QuoteRequestSerializer,
    RepairShopSerializer,
    ReviewSerializer,
    ServiceSerializer,
    VehicleTypeSerializer,
)
from .workflows import record_quote_event


def require_object_payload(request):
    if not isinstance(request.data, Mapping):
        raise ValidationError({"detail": "Le corps de la requête doit être un objet."})


class ServiceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Service.objects.filter(is_active=True)
    serializer_class = ServiceSerializer
    permission_classes = [permissions.AllowAny]


class VehicleTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = VehicleType.objects.filter(is_active=True)
    serializer_class = VehicleTypeSerializer
    permission_classes = [permissions.AllowAny]


class CustomerVehicleViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerVehicleSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        queryset = CustomerVehicle.objects.select_related("customer", "vehicle_type")
        if user.is_staff:
            return queryset
        return queryset.filter(customer=user)

    def perform_create(self, serializer):
        if self.request.user.role != User.Role.CUSTOMER:
            raise PermissionDenied("Seuls les clients peuvent enregistrer un véhicule.")
        serializer.save(customer=self.request.user)

    def perform_update(self, serializer):
        if (
            not self.request.user.is_staff
            and serializer.instance.customer_id != self.request.user.id
        ):
            raise PermissionDenied("Vous ne pouvez modifier que vos véhicules.")
        serializer.save()

    def perform_destroy(self, instance):
        if (
            not self.request.user.is_staff
            and instance.customer_id != self.request.user.id
        ):
            raise PermissionDenied("Vous ne pouvez supprimer que vos véhicules.")
        instance.delete()


class RepairShopViewSet(viewsets.ModelViewSet):
    serializer_class = RepairShopSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsShopOwnerOrReadOnly]
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    def get_queryset(self):
        queryset = RepairShop.objects.filter(is_active=True).select_related("owner")
        queryset = queryset.prefetch_related("services", "vehicle_types")
        queryset = queryset.annotate(
            average_rating=Avg("reviews__rating", filter=Q(reviews__is_approved=True)),
            approved_review_count=Count(
                "reviews", filter=Q(reviews__is_approved=True), distinct=True
            ),
        )

        params = self.request.query_params
        search = params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(description__icontains=search)
                | Q(district__icontains=search)
                | Q(city__icontains=search)
            )
        for param, field in (("city", "city"), ("district", "district")):
            value = params.get(param)
            if value:
                queryset = queryset.filter(**{f"{field}__icontains": value})
        vehicle = params.get("vehicle")
        if vehicle:
            queryset = queryset.filter(vehicle_types__slug=vehicle)
        service = params.get("service")
        if service:
            queryset = queryset.filter(services__slug=service)
        mobile = params.get("mobile_service")
        if mobile in {"true", "false"}:
            queryset = queryset.filter(mobile_service=(mobile == "true"))
        return queryset.distinct().order_by("name", "id")

    def perform_create(self, serializer):
        if self.request.user.role != User.Role.MECHANIC and not self.request.user.is_staff:
            raise PermissionDenied("Un compte réparateur est requis pour créer un atelier.")
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        if (
            not self.request.user.is_staff
            and serializer.instance.owner_id != self.request.user.id
        ):
            raise PermissionDenied("Vous ne pouvez modifier que vos propres ateliers.")
        serializer.save()

    def perform_destroy(self, instance):
        if (
            not self.request.user.is_staff
            and instance.owner_id != self.request.user.id
        ):
            raise PermissionDenied("Vous ne pouvez supprimer que vos propres ateliers.")
        instance.is_active = False
        instance.save(update_fields=("is_active", "updated_at"))

    @decorators.action(detail=True, methods=["get"])
    def reviews(self, request, pk=None):
        shop = self.get_object()
        queryset = Review.objects.filter(shop=shop, is_approved=True).select_related(
            "customer"
        )
        page = self.paginate_queryset(queryset)
        serializer = ReviewSerializer(page or queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return response.Response(serializer.data)


class QuoteRequestViewSet(viewsets.ModelViewSet):
    queryset = QuoteRequest.objects.all()
    serializer_class = QuoteRequestSerializer
    http_method_names = ["get", "post", "head", "options"]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = QuoteRequest.objects.select_related(
            "customer", "shop", "shop__owner", "vehicle_type", "vehicle"
        ).prefetch_related(
            "attachments",
            "messages__author",
            "offers__parts",
            "appointments",
            "events__actor",
        )
        if user.is_staff:
            return queryset
        return queryset.filter(Q(customer=user) | Q(shop__owner=user))

    def perform_create(self, serializer):
        if self.request.user.role != User.Role.CUSTOMER:
            raise PermissionDenied("Seuls les clients peuvent demander un devis.")
        with transaction.atomic():
            quote = serializer.save()
            record_quote_event(
                quote,
                self.request.user,
                "request_created",
                "Une nouvelle demande de réparation a été reçue.",
                quote.shop.owner,
            )

    def _require_shop_owner(self, request, quote):
        if not request.user.is_staff and (
            request.user.role != User.Role.MECHANIC
            or quote.shop.owner_id != request.user.id
        ):
            raise PermissionDenied("Seul le réparateur concerné peut effectuer cette action.")

    def _require_customer(self, request, quote):
        if not request.user.is_staff and (
            request.user.role != User.Role.CUSTOMER
            or quote.customer_id != request.user.id
        ):
            raise PermissionDenied("Seul le client à l'origine peut effectuer cette action.")

    @decorators.action(
        detail=True,
        methods=["get"],
        url_path=r"attachments/(?P<attachment_id>\d+)",
    )
    def attachment(self, request, pk=None, attachment_id=None):
        quote = self.get_object()
        attachment = get_object_or_404(
            quote.attachments, pk=attachment_id
        )
        content_type = mimetypes.guess_type(attachment.image.name)[0]
        file_response = FileResponse(
            attachment.image.open("rb"),
            content_type=content_type or "application/octet-stream",
        )
        file_response["Cache-Control"] = "private, no-store"
        file_response["X-Content-Type-Options"] = "nosniff"
        return file_response

    @decorators.action(detail=True, methods=["post"], url_path="accept-request")
    @transaction.atomic
    def accept_request(self, request, pk=None):
        quote = self.get_object()
        self._require_shop_owner(request, quote)
        if quote.status != QuoteRequest.Status.NEW:
            raise ValidationError("Seule une nouvelle demande peut être acceptée.")
        quote.status = QuoteRequest.Status.DISCUSSION
        quote.save(update_fields=("status", "updated_at"))
        record_quote_event(
            quote,
            request.user,
            "request_accepted",
            "Le réparateur a accepté d'étudier la demande.",
            quote.customer,
        )
        return response.Response(self.get_serializer(quote).data)

    @decorators.action(detail=True, methods=["post"], url_path="decline-request")
    @transaction.atomic
    def decline_request(self, request, pk=None):
        quote = self.get_object()
        self._require_shop_owner(request, quote)
        require_object_payload(request)
        if quote.status not in (
            QuoteRequest.Status.NEW,
            QuoteRequest.Status.DISCUSSION,
        ):
            raise ValidationError("Cette demande ne peut plus être refusée.")
        reason = request.data.get("reason", "")
        if not isinstance(reason, str) or len(reason) > 1000:
            raise ValidationError({"reason": "Le motif ne peut pas dépasser 1 000 caractères."})
        quote.refusal_reason = reason.strip()
        quote.status = QuoteRequest.Status.DECLINED
        quote.save(update_fields=("refusal_reason", "status", "updated_at"))
        record_quote_event(
            quote,
            request.user,
            "request_declined",
            "Le réparateur a refusé la demande.",
            quote.customer,
        )
        return response.Response(self.get_serializer(quote).data)

    @decorators.action(detail=True, methods=["post"])
    @transaction.atomic
    def message(self, request, pk=None):
        quote = self.get_object()
        require_object_payload(request)
        if request.user.is_staff:
            recipient = quote.customer
        elif quote.customer_id == request.user.id:
            recipient = quote.shop.owner
        elif (
            request.user.role == User.Role.MECHANIC
            and quote.shop.owner_id == request.user.id
        ):
            recipient = quote.customer
        else:
            raise PermissionDenied("Cette demande ne vous est pas accessible.")
        if quote.status not in (
            QuoteRequest.Status.NEW,
            QuoteRequest.Status.DISCUSSION,
            QuoteRequest.Status.ANSWERED,
            QuoteRequest.Status.QUOTE_SENT,
        ):
            raise ValidationError("Cette demande n'accepte plus de messages.")
        message = request.data.get("message")
        if not isinstance(message, str) or not message.strip():
            raise ValidationError({"message": "Un message est obligatoire."})
        if len(message.strip()) > 3000:
            raise ValidationError({"message": "Le message est limité à 3 000 caractères."})
        QuoteMessage.objects.create(
            quote=quote, author=request.user, message=message.strip()
        )
        if quote.status == QuoteRequest.Status.NEW:
            quote.status = QuoteRequest.Status.DISCUSSION
            quote.save(update_fields=("status", "updated_at"))
        record_quote_event(
            quote,
            request.user,
            "message_received",
            "Un nouveau message a été ajouté à la demande.",
            recipient,
        )
        quote.refresh_from_db()
        return response.Response(self.get_serializer(quote).data)

    @decorators.action(detail=True, methods=["post"])
    @transaction.atomic
    def offers(self, request, pk=None):
        quote = self.get_object()
        self._require_shop_owner(request, quote)
        if quote.status not in (
            QuoteRequest.Status.DISCUSSION,
            QuoteRequest.Status.ANSWERED,
            QuoteRequest.Status.ACCEPTED,
            QuoteRequest.Status.QUOTE_ACCEPTED,
            QuoteRequest.Status.APPOINTMENT_CONFIRMED,
            QuoteRequest.Status.IN_PROGRESS,
        ):
            raise ValidationError(
                "Un devis initial exige une discussion; un devis complémentaire doit concerner une intervention acceptée."
            )
        serializer = QuoteOfferSerializer(
            data=request.data, context={"request": request, "quote": quote}
        )
        serializer.is_valid(raise_exception=True)
        offer = serializer.save()
        record_quote_event(
            quote,
            request.user,
            "quote_sent",
            f"Le devis estimatif version {offer.version} a été envoyé.",
            quote.customer,
        )
        return response.Response(
            QuoteOfferSerializer(offer, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @decorators.action(detail=True, methods=["post"], url_path="request-changes")
    @transaction.atomic
    def request_changes(self, request, pk=None):
        quote = self.get_object()
        self._require_customer(request, quote)
        require_object_payload(request)
        if quote.status != QuoteRequest.Status.QUOTE_SENT:
            raise ValidationError("Seul un devis en attente peut être modifié.")
        reason = request.data.get("reason", "")
        if not isinstance(reason, str) or len(reason) > 1000:
            raise ValidationError({"reason": "Le motif ne peut pas dépasser 1 000 caractères."})
        offer = quote.offers.filter(status=QuoteOffer.Status.SENT).first()
        if not offer:
            raise ValidationError("Aucun devis actif n'a été trouvé.")
        offer.status = QuoteOffer.Status.CHANGE_REQUESTED
        offer.save(update_fields=("status",))
        quote.status = QuoteRequest.Status.DISCUSSION
        quote.save(update_fields=("status", "updated_at"))
        record_quote_event(
            quote,
            request.user,
            "quote_changes_requested",
            reason.strip() or "Le client demande une modification du devis.",
            quote.shop.owner,
        )
        quote.refresh_from_db()
        return response.Response(self.get_serializer(quote).data)

    @decorators.action(detail=True, methods=["post"])
    @transaction.atomic
    def appointments(self, request, pk=None):
        quote = self.get_object()
        self._require_shop_owner(request, quote)
        require_object_payload(request)
        if quote.status != QuoteRequest.Status.QUOTE_ACCEPTED:
            raise ValidationError("Un rendez-vous ne peut être proposé qu'après acceptation du devis.")
        try:
            scheduled_at = serializers.DateTimeField().run_validation(
                request.data.get("scheduled_at")
            )
        except serializers.ValidationError as exc:
            raise ValidationError({"scheduled_at": exc.detail}) from exc
        if scheduled_at <= timezone.now():
            raise ValidationError({"scheduled_at": "Choisissez une date future."})
        accepted_offer = quote.offers.filter(status=QuoteOffer.Status.ACCEPTED).first()
        if accepted_offer is None:
            raise ValidationError("Aucun devis accepté n'a été trouvé.")
        duration = accepted_offer.estimated_duration_minutes
        note = request.data.get("note", "")
        if not isinstance(note, str) or len(note) > 1000:
            raise ValidationError({"note": "La note ne peut pas dépasser 1 000 caractères."})
        if self._has_appointment_conflict(quote.shop_id, scheduled_at, duration):
            raise ValidationError({"scheduled_at": "Ce créneau chevauche un rendez-vous confirmé."})
        appointment = Appointment.objects.create(
            quote=quote,
            proposed_by=request.user,
            scheduled_at=scheduled_at,
            duration_minutes=duration,
            note=note.strip(),
        )
        record_quote_event(
            quote,
            request.user,
            "appointment_proposed",
            "Le réparateur a proposé une date de rendez-vous.",
            quote.customer,
        )
        return response.Response(
            AppointmentSerializer(appointment).data, status=status.HTTP_201_CREATED
        )

    @staticmethod
    def _has_appointment_conflict(shop_id, scheduled_at, duration):
        proposed_end = scheduled_at + timedelta(minutes=duration)
        confirmed = Appointment.objects.filter(
            quote__shop_id=shop_id, status=Appointment.Status.CONFIRMED
        ).select_related("quote")
        return any(
            appointment.scheduled_at < proposed_end
            and appointment.scheduled_at
            + timedelta(minutes=appointment.duration_minutes)
            > scheduled_at
            for appointment in confirmed
        )

    @decorators.action(detail=True, methods=["post"])
    @transaction.atomic
    def respond(self, request, pk=None):
        quote = self.get_object()
        self._require_shop_owner(request, quote)
        if quote.status not in (
            QuoteRequest.Status.NEW,
            QuoteRequest.Status.DISCUSSION,
        ):
            raise ValidationError("Cette demande a déjà été traitée.")

        if not isinstance(request.data, Mapping):
            raise ValidationError({"response": "Le corps de la requête doit être un objet."})
        answer = request.data.get("response")
        if not isinstance(answer, str) or not answer.strip():
            raise ValidationError({"response": "Une réponse est obligatoire."})
        answer = answer.strip()
        if len(answer) > 3000:
            raise ValidationError(
                {"response": "La réponse ne peut pas dépasser 3 000 caractères."}
            )
        QuoteMessage.objects.create(quote=quote, author=request.user, message=answer)
        quote.mechanic_response = answer
        if quote.status == QuoteRequest.Status.NEW:
            quote.status = QuoteRequest.Status.ANSWERED
        quote.save(update_fields=("mechanic_response", "status", "updated_at"))
        record_quote_event(
            quote,
            request.user,
            "message_received",
            "Le réparateur a répondu à la demande.",
            quote.customer,
        )
        quote.refresh_from_db()
        return response.Response(self.get_serializer(quote).data)

    @decorators.action(detail=True, methods=["post"])
    @transaction.atomic
    def decide(self, request, pk=None):
        quote = self.get_object()
        self._require_customer(request, quote)
        if not isinstance(request.data, Mapping):
            raise ValidationError({"decision": "Le corps de la requête doit être un objet."})
        decision = request.data.get("decision")
        if decision not in (QuoteRequest.Status.ACCEPTED, QuoteRequest.Status.DECLINED):
            raise ValidationError({"decision": "Choisissez accepted ou declined."})
        if quote.status == QuoteRequest.Status.QUOTE_SENT:
            offer = quote.offers.filter(status=QuoteOffer.Status.SENT).first()
            if offer is None:
                raise ValidationError("Aucun devis actif n'a été trouvé.")
            if (
                decision == QuoteRequest.Status.ACCEPTED
                and offer.valid_until < timezone.localdate()
            ):
                raise ValidationError(
                    "Ce devis estimatif a expiré. Demandez une nouvelle proposition au réparateur."
                )
            if decision == QuoteRequest.Status.ACCEPTED:
                offer.status = QuoteOffer.Status.ACCEPTED
                quote.status = (
                    offer.resume_status
                    if offer.is_supplemental and offer.resume_status
                    else QuoteRequest.Status.QUOTE_ACCEPTED
                )
                action = "quote_accepted"
                details = (
                    "Le client a accepté le devis complémentaire."
                    if offer.is_supplemental
                    else "Le client a accepté le devis estimatif."
                )
            else:
                offer.status = QuoteOffer.Status.DECLINED
                quote.status = (
                    offer.resume_status
                    if offer.is_supplemental and offer.resume_status
                    else QuoteRequest.Status.QUOTE_DECLINED
                )
                action = "quote_declined"
                details = (
                    "Le client a refusé le devis complémentaire; le devis précédemment accepté reste inchangé."
                    if offer.is_supplemental
                    else "Le client a refusé le devis estimatif."
                )
            offer.save(update_fields=("status",))
            quote.save(update_fields=("status", "updated_at"))
            record_quote_event(
                quote, request.user, action, details, quote.shop.owner
            )
            quote.refresh_from_db()
            return response.Response(self.get_serializer(quote).data)
        if quote.status != QuoteRequest.Status.ANSWERED:
            raise ValidationError(
                "Seule une demande répondue ou un devis envoyé peut être accepté ou refusé."
            )
        quote.status = decision
        quote.save(update_fields=("status", "updated_at"))
        record_quote_event(
            quote,
            request.user,
            "request_decided",
            "Le client a répondu à la proposition du réparateur.",
            quote.shop.owner,
        )
        return response.Response(self.get_serializer(quote).data)

    @decorators.action(detail=True, methods=["post"], url_path="report")
    @transaction.atomic
    def report(self, request, pk=None):
        quote = self.get_object()
        require_object_payload(request)
        if not request.user.is_staff and request.user.id not in (
            quote.customer_id,
            quote.shop.owner_id,
        ):
            raise PermissionDenied("Seuls les participants peuvent signaler une demande.")
        reason = request.data.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            raise ValidationError({"reason": "Un motif est obligatoire."})
        if len(reason.strip()) > 2000:
            raise ValidationError({"reason": "Le motif ne peut pas dépasser 2 000 caractères."})
        report = QuoteReport.objects.create(
            quote=quote, reporter=request.user, reason=reason.strip()
        )
        if request.user.id == quote.customer_id:
            recipient = quote.shop.owner
        else:
            recipient = quote.customer
        record_quote_event(
            quote,
            request.user,
            "reported",
            "Un signalement a été transmis à l'administration.",
            recipient if not request.user.is_staff else None,
        )
        return response.Response(
            QuoteReportSerializer(report).data, status=status.HTTP_201_CREATED
        )

    @decorators.action(detail=True, methods=["post"])
    @transaction.atomic
    def complete(self, request, pk=None):
        quote = self.get_object()
        if (
            not request.user.is_staff
            and quote.customer_id != request.user.id
            and quote.shop.owner_id != request.user.id
        ):
            raise PermissionDenied(
                "Seuls le client et le réparateur concernés peuvent confirmer la fin."
            )
        if quote.status not in (
            QuoteRequest.Status.ACCEPTED,
            QuoteRequest.Status.IN_PROGRESS,
        ):
            raise ValidationError("Seule une réparation acceptée ou en cours peut être terminée.")
        quote.status = QuoteRequest.Status.COMPLETED
        quote.save(update_fields=("status", "updated_at"))
        return response.Response(self.get_serializer(quote).data)

    @decorators.action(detail=True, methods=["post"])
    @transaction.atomic
    def start(self, request, pk=None):
        quote = self.get_object()
        self._require_shop_owner(request, quote)
        allowed_statuses = (QuoteRequest.Status.ACCEPTED,)
        if quote.status in (
            QuoteRequest.Status.QUOTE_ACCEPTED,
            QuoteRequest.Status.APPOINTMENT_CONFIRMED,
        ):
            if not quote.appointments.filter(
                status=Appointment.Status.CONFIRMED
            ).exists():
                raise ValidationError("Un rendez-vous confirmé est requis avant de démarrer.")
            allowed_statuses = (
                QuoteRequest.Status.QUOTE_ACCEPTED,
                QuoteRequest.Status.APPOINTMENT_CONFIRMED,
            )
        if quote.status not in allowed_statuses:
            raise ValidationError("La demande doit être acceptée avant de démarrer.")
        quote.status = QuoteRequest.Status.IN_PROGRESS
        quote.save(update_fields=("status", "updated_at"))
        record_quote_event(
            quote,
            request.user,
            "work_started",
            "L'intervention a commencé.",
            quote.customer,
        )
        return response.Response(self.get_serializer(quote).data)

    @decorators.action(detail=True, methods=["post"])
    @transaction.atomic
    def cancel(self, request, pk=None):
        quote = self.get_object()
        self._require_customer(request, quote)
        if quote.status not in (
            QuoteRequest.Status.NEW,
            QuoteRequest.Status.ANSWERED,
            QuoteRequest.Status.DISCUSSION,
            QuoteRequest.Status.QUOTE_SENT,
            QuoteRequest.Status.QUOTE_ACCEPTED,
        ):
            raise ValidationError("Cette demande ne peut plus être annulée.")
        quote.status = QuoteRequest.Status.CANCELLED
        quote.save(update_fields=("status", "updated_at"))
        record_quote_event(
            quote,
            request.user,
            "request_cancelled",
            "Le client a annulé la demande.",
            quote.shop.owner,
        )
        return response.Response(self.get_serializer(quote).data)


class AppointmentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        queryset = Appointment.objects.select_related(
            "quote", "quote__shop", "quote__customer", "proposed_by"
        )
        if user.is_staff:
            return queryset
        return queryset.filter(Q(quote__customer=user) | Q(quote__shop__owner=user))

    @decorators.action(detail=True, methods=["post"])
    @transaction.atomic
    def confirm(self, request, pk=None):
        appointment = self.get_object()
        quote = appointment.quote
        if not request.user.is_staff and (
            request.user.role != User.Role.CUSTOMER
            or quote.customer_id != request.user.id
        ):
            raise PermissionDenied("Seul le client concerné peut choisir ce créneau.")
        if (
            quote.status != QuoteRequest.Status.QUOTE_ACCEPTED
            or appointment.status != Appointment.Status.PROPOSED
        ):
            raise ValidationError("Ce créneau ne peut plus être confirmé.")
        if appointment.scheduled_at <= timezone.now():
            raise ValidationError("Ce créneau est déjà passé.")
        RepairShop.objects.select_for_update().get(pk=quote.shop_id)
        if QuoteRequestViewSet._has_appointment_conflict(
            quote.shop_id, appointment.scheduled_at, appointment.duration_minutes
        ):
            raise ValidationError("Ce créneau chevauche un rendez-vous déjà confirmé.")
        appointment.status = Appointment.Status.CONFIRMED
        appointment.save(update_fields=("status", "updated_at"))
        quote.appointments.filter(status=Appointment.Status.PROPOSED).exclude(
            pk=appointment.pk
        ).update(status=Appointment.Status.DECLINED)
        quote.status = QuoteRequest.Status.APPOINTMENT_CONFIRMED
        quote.save(update_fields=("status", "updated_at"))
        record_quote_event(
            quote,
            request.user,
            "appointment_confirmed",
            "Le client a confirmé le rendez-vous.",
            quote.shop.owner,
        )
        return response.Response(self.get_serializer(appointment).data)

    @decorators.action(detail=True, methods=["post"])
    @transaction.atomic
    def cancel(self, request, pk=None):
        appointment = self.get_object()
        quote = appointment.quote
        if not request.user.is_staff and request.user.id not in (
            quote.customer_id,
            quote.shop.owner_id,
        ):
            raise PermissionDenied("Seuls les participants peuvent annuler le rendez-vous.")
        if appointment.status not in (
            Appointment.Status.PROPOSED,
            Appointment.Status.CONFIRMED,
        ):
            raise ValidationError("Ce rendez-vous ne peut plus être annulé.")
        if appointment.scheduled_at <= timezone.now():
            raise ValidationError("Un rendez-vous passé ne peut plus être annulé.")
        appointment.status = Appointment.Status.CANCELLED
        appointment.save(update_fields=("status", "updated_at"))
        if quote.status == QuoteRequest.Status.APPOINTMENT_CONFIRMED:
            quote.status = QuoteRequest.Status.QUOTE_ACCEPTED
            quote.save(update_fields=("status", "updated_at"))
        recipient = (
            quote.shop.owner
            if request.user.id == quote.customer_id
            else quote.customer
        )
        record_quote_event(
            quote,
            request.user,
            "appointment_cancelled",
            "Le rendez-vous a été annulé.",
            recipient,
        )
        return response.Response(self.get_serializer(appointment).data)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        queryset = Notification.objects.select_related("quote")
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(recipient=self.request.user)

    @decorators.action(detail=True, methods=["post"], url_path="read")
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        if not request.user.is_staff and notification.recipient_id != request.user.id:
            raise PermissionDenied("Cette notification ne vous appartient pas.")
        notification.is_read = True
        notification.save(update_fields=("is_read",))
        return response.Response(self.get_serializer(notification).data)


class QuoteReportViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = QuoteReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        queryset = QuoteReport.objects.select_related(
            "quote", "reporter", "quote__shop"
        )
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(reporter=self.request.user)

    def create(self, request, *args, **kwargs):
        raise PermissionDenied("Signalez une demande depuis /api/quotes/{id}/report/.")

    @decorators.action(detail=True, methods=["post"])
    @transaction.atomic
    def resolve(self, request, pk=None):
        if not request.user.is_staff:
            raise PermissionDenied("Seuls les administrateurs peuvent traiter un signalement.")
        report = self.get_object()
        report.status = QuoteReport.Status.RESOLVED
        report.save(update_fields=("status",))
        record_quote_event(
            report.quote,
            request.user,
            "report_resolved",
            "L'administration a traité le signalement.",
            report.reporter,
        )
        return response.Response(self.get_serializer(report).data)


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    http_method_names = ["get", "post", "head", "options", "delete"]

    def get_permissions(self):
        if self.action in ("create", "destroy"):
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        queryset = Review.objects.select_related("customer", "shop")
        if self.request.user.is_staff:
            return queryset
        if self.request.user.is_authenticated:
            return queryset.filter(
                Q(is_approved=True) | Q(customer=self.request.user)
            )
        return queryset.filter(is_approved=True)

    def perform_create(self, serializer):
        user = self.request.user
        if user.role != User.Role.CUSTOMER:
            raise PermissionDenied("Seuls les clients peuvent laisser un avis.")
        shop = serializer.validated_data["shop"]
        has_completed_quote = QuoteRequest.objects.filter(
            customer=user, shop=shop, status=QuoteRequest.Status.COMPLETED
        ).exists()
        if not has_completed_quote:
            raise ValidationError(
                "Un devis terminé auprès de cet atelier est nécessaire pour laisser un avis."
            )
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.is_staff and instance.customer_id != self.request.user.id:
            raise PermissionDenied("Vous ne pouvez supprimer que vos propres avis.")
        instance.delete()
