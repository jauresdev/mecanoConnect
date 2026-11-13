from collections.abc import Mapping

from django.db.models import Avg, Count, Q
from rest_framework import decorators, permissions, response, status, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import User

from .models import QuoteRequest, RepairShop, Review, Service, VehicleType
from .permissions import IsShopOwnerOrReadOnly
from .serializers import (
    QuoteRequestSerializer,
    RepairShopSerializer,
    ReviewSerializer,
    ServiceSerializer,
    VehicleTypeSerializer,
)


class ServiceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Service.objects.filter(is_active=True)
    serializer_class = ServiceSerializer
    permission_classes = [permissions.AllowAny]


class VehicleTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = VehicleType.objects.filter(is_active=True)
    serializer_class = VehicleTypeSerializer
    permission_classes = [permissions.AllowAny]


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
        if user.is_staff:
            return QuoteRequest.objects.select_related(
                "customer", "shop", "vehicle_type"
            )
        return QuoteRequest.objects.filter(
            Q(customer=user) | Q(shop__owner=user)
        ).select_related("customer", "shop", "vehicle_type")

    def perform_create(self, serializer):
        if self.request.user.role != User.Role.CUSTOMER:
            raise PermissionDenied("Seuls les clients peuvent demander un devis.")
        serializer.save()

    @decorators.action(detail=True, methods=["post"])
    def respond(self, request, pk=None):
        quote = self.get_object()
        if not request.user.is_staff and quote.shop.owner_id != request.user.id:
            raise PermissionDenied("Seul le réparateur concerné peut répondre.")
        if quote.status != QuoteRequest.Status.NEW:
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
        quote.mechanic_response = answer
        quote.status = QuoteRequest.Status.ANSWERED
        quote.save(update_fields=("mechanic_response", "status", "updated_at"))
        return response.Response(self.get_serializer(quote).data)

    @decorators.action(detail=True, methods=["post"])
    def decide(self, request, pk=None):
        quote = self.get_object()
        if not request.user.is_staff and quote.customer_id != request.user.id:
            raise PermissionDenied("Seul le client à l'origine peut décider.")
        if quote.status != QuoteRequest.Status.ANSWERED:
            raise ValidationError("Seule une demande répondue peut être acceptée ou refusée.")
        if not isinstance(request.data, Mapping):
            raise ValidationError({"decision": "Le corps de la requête doit être un objet."})
        decision = request.data.get("decision")
        if decision not in (QuoteRequest.Status.ACCEPTED, QuoteRequest.Status.DECLINED):
            raise ValidationError({"decision": "Choisissez accepted ou declined."})
        quote.status = decision
        quote.save(update_fields=("status", "updated_at"))
        return response.Response(self.get_serializer(quote).data)

    @decorators.action(detail=True, methods=["post"])
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
    def start(self, request, pk=None):
        quote = self.get_object()
        if not request.user.is_staff and quote.shop.owner_id != request.user.id:
            raise PermissionDenied("Seul le réparateur concerné peut démarrer la réparation.")
        if quote.status != QuoteRequest.Status.ACCEPTED:
            raise ValidationError("La demande doit être acceptée par le client avant de démarrer.")
        quote.status = QuoteRequest.Status.IN_PROGRESS
        quote.save(update_fields=("status", "updated_at"))
        return response.Response(self.get_serializer(quote).data)

    @decorators.action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        quote = self.get_object()
        if not request.user.is_staff and quote.customer_id != request.user.id:
            raise PermissionDenied("Seul le client à l'origine peut annuler.")
        if quote.status not in (
            QuoteRequest.Status.NEW,
            QuoteRequest.Status.ANSWERED,
        ):
            raise ValidationError("Cette demande ne peut plus être annulée.")
        quote.status = QuoteRequest.Status.CANCELLED
        quote.save(update_fields=("status", "updated_at"))
        return response.Response(self.get_serializer(quote).data)


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
