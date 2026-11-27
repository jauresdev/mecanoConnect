from datetime import time

from config.file_validation import validate_image_upload
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import (
    Appointment,
    CustomerVehicle,
    Notification,
    QuoteAttachment,
    QuoteEvent,
    QuoteMessage,
    QuoteOffer,
    QuotePart,
    QuoteReport,
    QuoteRequest,
    RepairShop,
    RepairShopPhoto,
    Review,
    Service,
    VehicleType,
)


User = get_user_model()


class VehicleTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleType
        fields = ("id", "name", "slug")


class ServiceSerializer(serializers.ModelSerializer):
    vehicle_types = serializers.PrimaryKeyRelatedField(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Service
        fields = ("id", "name", "slug", "vehicle_types")


class CustomerVehicleSerializer(serializers.ModelSerializer):
    vehicle_type_name = serializers.CharField(
        source="vehicle_type.name", read_only=True
    )

    class Meta:
        model = CustomerVehicle
        fields = (
            "id",
            "vehicle_type",
            "vehicle_type_name",
            "make",
            "model",
            "year",
            "registration",
            "created_at",
        )
        read_only_fields = ("id", "vehicle_type_name", "created_at")

    def validate_vehicle_type(self, vehicle_type):
        if not vehicle_type.is_active:
            raise serializers.ValidationError("Ce type de véhicule est indisponible.")
        return vehicle_type

    def validate_year(self, year):
        if year is not None and not 1886 <= year <= timezone.localdate().year + 1:
            raise serializers.ValidationError("L’année du véhicule est invalide.")
        return year

    def validate_make(self, make):
        if not make.strip():
            raise serializers.ValidationError("La marque est obligatoire.")
        return make.strip()

    def validate_model(self, model):
        if not model.strip():
            raise serializers.ValidationError("Le modèle est obligatoire.")
        return model.strip()


class QuoteAttachmentSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = QuoteAttachment
        fields = ("id", "image", "created_at")
        read_only_fields = fields

    @extend_schema_field(serializers.CharField())
    def get_image(self, attachment):
        return (
            f"/quotes/{attachment.quote_id}/attachments/{attachment.id}/"
        )


class QuoteMessageSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = QuoteMessage
        fields = ("id", "author", "author_name", "message", "created_at")
        read_only_fields = fields

    @extend_schema_field(serializers.CharField())
    def get_author_name(self, message):
        return message.author.get_full_name() or message.author.username


class QuotePartSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuotePart
        fields = ("id", "name", "quantity", "unit_price")
        read_only_fields = ("id",)

    def validate_quantity(self, quantity):
        if quantity < 1 or quantity > 100:
            raise serializers.ValidationError("La quantité doit être comprise entre 1 et 100.")
        return quantity

    def validate_unit_price(self, price):
        if price < 0:
            raise serializers.ValidationError("Le prix ne peut pas être négatif.")
        return price


class QuoteOfferSerializer(serializers.ModelSerializer):
    parts = QuotePartSerializer(many=True, max_length=100)
    total = serializers.DecimalField(
        max_digits=20, decimal_places=0, read_only=True
    )
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = QuoteOffer
        fields = (
            "id",
            "version",
            "description",
            "parts",
            "labor_cost",
            "travel_cost",
            "total",
            "is_expired",
            "estimated_duration_minutes",
            "valid_until",
            "conditions",
            "currency",
            "is_supplemental",
            "resume_status",
            "status",
            "created_at",
        )
        read_only_fields = (
            "id",
            "version",
            "currency",
            "is_supplemental",
            "resume_status",
            "status",
            "created_at",
            "is_expired",
        )

    def validate_labor_cost(self, cost):
        if cost < 0:
            raise serializers.ValidationError("Le coût ne peut pas être négatif.")
        return cost

    def validate_travel_cost(self, cost):
        if cost < 0:
            raise serializers.ValidationError("Les frais ne peuvent pas être négatifs.")
        return cost

    def validate_estimated_duration_minutes(self, duration):
        if not 1 <= duration <= 525600:
            raise serializers.ValidationError("La durée doit être comprise entre 1 minute et un an.")
        return duration

    def validate_valid_until(self, valid_until):
        if valid_until < timezone.localdate():
            raise serializers.ValidationError("La validité ne peut pas être dans le passé.")
        return valid_until

    @extend_schema_field(serializers.BooleanField())
    def get_is_expired(self, offer):
        return (
            offer.status == QuoteOffer.Status.SENT
            and offer.valid_until < timezone.localdate()
        )

    def validate(self, attrs):
        if not attrs.get("parts"):
            attrs["parts"] = []
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        parts = validated_data.pop("parts")
        quote = self.context["quote"]
        change_requested_offer = quote.offers.filter(
            status=QuoteOffer.Status.CHANGE_REQUESTED
        ).first()
        active_statuses = (
            QuoteRequest.Status.ACCEPTED,
            QuoteRequest.Status.QUOTE_ACCEPTED,
            QuoteRequest.Status.APPOINTMENT_CONFIRMED,
            QuoteRequest.Status.IN_PROGRESS,
        )
        is_supplemental = bool(
            (change_requested_offer and change_requested_offer.is_supplemental)
            or quote.status in active_statuses
        )
        resume_status = ""
        if is_supplemental:
            resume_status = (
                change_requested_offer.resume_status
                if change_requested_offer and change_requested_offer.resume_status
                else quote.status
            )
        current_offer = quote.offers.filter(
            status__in=(
                QuoteOffer.Status.SENT,
                QuoteOffer.Status.CHANGE_REQUESTED,
            )
        ).first()
        if current_offer:
            current_offer.status = QuoteOffer.Status.SUPERSEDED
            current_offer.save(update_fields=("status",))
        version = (quote.offers.order_by("-version").values_list("version", flat=True).first() or 0) + 1
        offer = QuoteOffer.objects.create(
            quote=quote,
            version=version,
            is_supplemental=is_supplemental,
            resume_status=resume_status,
            **validated_data,
        )
        QuotePart.objects.bulk_create(
            [QuotePart(offer=offer, **part) for part in parts]
        )
        quote.status = QuoteRequest.Status.QUOTE_SENT
        quote.save(update_fields=("status", "updated_at"))
        return offer


class AppointmentSerializer(serializers.ModelSerializer):
    shop_name = serializers.CharField(source="quote.shop.name", read_only=True)

    class Meta:
        model = Appointment
        fields = (
            "id",
            "quote_id",
            "shop_name",
            "scheduled_at",
            "duration_minutes",
            "status",
            "note",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class QuoteEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = QuoteEvent
        fields = ("id", "actor_name", "action", "details", "created_at")
        read_only_fields = fields

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_actor_name(self, event):
        if not event.actor:
            return None
        return event.actor.get_full_name() or event.actor.username


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ("id", "quote", "event", "message", "is_read", "created_at")
        read_only_fields = fields


class QuoteReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuoteReport
        fields = ("id", "quote", "reporter", "reason", "status", "created_at")
        read_only_fields = ("id", "reporter", "status", "created_at")


class ReviewSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(
        source="customer.first_name", read_only=True
    )
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = (
            "id",
            "shop",
            "customer_name",
            "rating",
            "comment",
            "is_mine",
            "is_approved",
            "created_at",
        )
        read_only_fields = (
            "id",
            "customer_name",
            "is_mine",
            "is_approved",
            "created_at",
        )

    @extend_schema_field(serializers.BooleanField())
    def get_is_mine(self, review):
        request = self.context.get("request")
        return bool(
            request
            and request.user.is_authenticated
            and review.customer_id == request.user.id
        )

    def validate_shop(self, shop):
        if not shop.is_active:
            raise serializers.ValidationError("Cet atelier n'accepte plus d'avis.")
        request = self.context.get("request")
        if request and Review.objects.filter(
            shop=shop, customer=request.user
        ).exists():
            raise serializers.ValidationError("Vous avez déjà laissé un avis pour cet atelier.")
        return shop

    def create(self, validated_data):
        review = Review.objects.create(
            customer=self.context["request"].user, **validated_data
        )
        return review


class RepairShopSerializer(serializers.ModelSerializer):
    WEEK_DAYS = {
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    }

    services = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Service.objects.filter(is_active=True),
        required=False,
    )
    vehicle_types = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=VehicleType.objects.filter(is_active=True),
        required=False,
    )
    owner_name = serializers.SerializerMethodField()
    owner_profile_photo = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    years_experience = serializers.IntegerField(
        min_value=0,
        max_value=80,
        required=False,
        allow_null=True,
    )
    gallery = serializers.SerializerMethodField()

    class Meta:
        model = RepairShop
        fields = (
            "id",
            "owner",
            "owner_name",
            "owner_profile_photo",
            "name",
            "business_type",
            "description",
            "years_experience",
            "city",
            "district",
            "address",
            "latitude",
            "longitude",
            "phone",
            "whatsapp",
            "photo",
            "gallery",
            "services",
            "vehicle_types",
            "mobile_service",
            "opening_hours",
            "is_verified",
            "average_rating",
            "review_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "owner",
            "owner_name",
            "owner_profile_photo",
            "gallery",
            "is_verified",
            "average_rating",
            "review_count",
            "created_at",
            "updated_at",
        )

    def validate_photo(self, photo):
        if photo:
            return validate_image_upload(photo)
        return photo

    def validate_opening_hours(self, opening_hours):
        if not isinstance(opening_hours, dict):
            raise serializers.ValidationError(
                "Les horaires doivent être renseignés par jour."
            )
        unknown_days = set(opening_hours) - self.WEEK_DAYS
        if unknown_days:
            raise serializers.ValidationError("Un jour de la semaine est invalide.")
        for day, hours in opening_hours.items():
            if hours is None:
                continue
            if not isinstance(hours, dict) or set(hours) != {"open", "close"}:
                raise serializers.ValidationError(
                    f"Les horaires de {day} doivent inclure ouverture et fermeture."
                )
            try:
                opening_time = time.fromisoformat(hours["open"])
                closing_time = time.fromisoformat(hours["close"])
            except (TypeError, ValueError):
                raise serializers.ValidationError(
                    f"Les heures de {day} sont invalides."
                ) from None
            if opening_time >= closing_time:
                raise serializers.ValidationError(
                    f"La fermeture de {day} doit être après l’ouverture."
                )
        return opening_hours

    @extend_schema_field(serializers.CharField())
    def get_owner_name(self, shop):
        return shop.owner.get_full_name() or shop.owner.username

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_owner_profile_photo(self, shop):
        if not shop.owner.profile_photo:
            return None

        request = self.context.get("request")
        url = shop.owner.profile_photo.url
        return request.build_absolute_uri(url) if request else url

    @extend_schema_field(serializers.ListField(child=serializers.URLField()))
    def get_gallery(self, shop):
        request = self.context.get("request")
        return [
            request.build_absolute_uri(photo.photo.url) if request else photo.photo.url
            for photo in shop.gallery.all()
        ]

    @extend_schema_field(serializers.FloatField(allow_null=True))
    def get_average_rating(self, shop):
        return getattr(shop, "average_rating", None)

    @extend_schema_field(serializers.IntegerField())
    def get_review_count(self, shop):
        return getattr(shop, "approved_review_count", 0)

    def validate(self, attrs):
        request = self.context.get("request")
        if request and request.method in ("POST", "PUT", "PATCH"):
            if request.user.role != User.Role.MECHANIC and not request.user.is_staff:
                raise serializers.ValidationError(
                    "Seuls les comptes réparateur peuvent gérer un atelier."
                )

            vehicle_types = attrs.get(
                "vehicle_types",
                self.instance.vehicle_types.all() if self.instance else (),
            )
            allowed_vehicle_slugs = {
                User.VehicleScope.AUTO: {"voiture"},
                User.VehicleScope.MOTO: {"moto"},
                User.VehicleScope.BOTH: {"voiture", "moto"},
            }.get(request.user.vehicle_scope)

            if allowed_vehicle_slugs is not None and vehicle_types:
                unsupported = [
                    vehicle.name
                    for vehicle in vehicle_types
                    if vehicle.slug not in allowed_vehicle_slugs
                ]
                if unsupported:
                    raise serializers.ValidationError(
                        {
                            "vehicle_types": (
                                "Votre compte ne peut pas gérer ces véhicules : "
                                + ", ".join(unsupported)
                            )
                        }
                    )

            services = attrs.get(
                "services",
                self.instance.services.all() if self.instance else (),
            )
            if vehicle_types and services:
                selected_vehicle_ids = {vehicle.pk for vehicle in vehicle_types}
                incompatible = [
                    service.name
                    for service in services
                    if service.vehicle_types.exists()
                    and not service.vehicle_types.filter(
                        pk__in=selected_vehicle_ids
                    ).exists()
                ]
                if incompatible:
                    raise serializers.ValidationError(
                        {
                            "services": (
                                "Ces spécialités ne correspondent pas aux "
                                "véhicules sélectionnés : "
                                + ", ".join(incompatible)
                            )
                        }
                    )
        return attrs


class RepairShopPhotoSerializer(serializers.ModelSerializer):
    photo = serializers.ImageField(validators=[validate_image_upload])

    class Meta:
        model = RepairShopPhoto
        fields = ("id", "photo", "created_at")
        read_only_fields = ("id", "created_at")


class QuoteRequestSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()
    shop_name = serializers.CharField(source="shop.name", read_only=True)
    vehicle_details = CustomerVehicleSerializer(source="vehicle", read_only=True)
    attachments = QuoteAttachmentSerializer(many=True, read_only=True)
    messages = QuoteMessageSerializer(many=True, read_only=True)
    offers = QuoteOfferSerializer(many=True, read_only=True)
    appointments = AppointmentSerializer(many=True, read_only=True)
    events = QuoteEventSerializer(many=True, read_only=True)
    images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        max_length=4,
    )

    class Meta:
        model = QuoteRequest
        fields = (
            "id",
            "customer",
            "customer_name",
            "shop",
            "shop_name",
            "vehicle_type",
            "vehicle",
            "vehicle_details",
            "vehicle_model",
            "problem",
            "urgency",
            "category",
            "location",
            "service_mode",
            "availability",
            "refusal_reason",
            "status",
            "mechanic_response",
            "images",
            "attachments",
            "messages",
            "offers",
            "appointments",
            "events",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "customer",
            "customer_name",
            "shop_name",
            "status",
            "mechanic_response",
            "refusal_reason",
            "vehicle_details",
            "attachments",
            "messages",
            "offers",
            "appointments",
            "events",
            "created_at",
            "updated_at",
        )

    @extend_schema_field(serializers.CharField())
    def get_customer_name(self, quote):
        return quote.customer.get_full_name() or quote.customer.username

    def validate_problem(self, problem):
        if not problem.strip():
            raise serializers.ValidationError("Décrivez le problème rencontré.")
        return problem.strip()

    def validate_vehicle_model(self, vehicle_model):
        if not vehicle_model.strip():
            raise serializers.ValidationError("Indiquez le modèle du véhicule.")
        return vehicle_model.strip()

    def validate_location(self, location):
        return location.strip()

    def validate_availability(self, availability):
        return availability.strip()

    def validate(self, attrs):
        request = self.context["request"]
        if request.method == "POST":
            submitted_data = request.data
            is_structured_request = any(
                field in submitted_data
                for field in ("category", "vehicle", "service_mode", "availability")
            )
            if is_structured_request:
                if not attrs.get("location", "").strip():
                    raise serializers.ValidationError(
                        {"location": "Indiquez votre quartier ou une localisation utile."}
                    )
                if not attrs.get("availability", "").strip():
                    raise serializers.ValidationError(
                        {"availability": "Indiquez au moins une disponibilité."}
                    )
            shop = attrs["shop"]
            if not shop.is_active:
                raise serializers.ValidationError(
                    {"shop": "Cet atelier n'accepte pas de demandes actuellement."}
                )
            if shop.owner_id == request.user.id:
                raise serializers.ValidationError(
                    {"shop": "Vous ne pouvez pas demander un devis à votre atelier."}
                )
            if attrs["vehicle_type"] not in shop.vehicle_types.all():
                raise serializers.ValidationError(
                    {"vehicle_type": "Cet atelier ne prend pas en charge ce véhicule."}
                )
            vehicle = attrs.get("vehicle")
            if vehicle:
                if vehicle.customer_id != request.user.id:
                    raise serializers.ValidationError(
                        {"vehicle": "Ce véhicule n'appartient pas à votre compte."}
                    )
                if vehicle.vehicle_type_id != attrs["vehicle_type"].id:
                    raise serializers.ValidationError(
                        {"vehicle": "Le type du véhicule enregistré ne correspond pas."}
                    )
            if attrs.get("service_mode") == QuoteRequest.ServiceMode.ON_SITE and not shop.mobile_service:
                raise serializers.ValidationError(
                    {"service_mode": "Cet atelier ne propose pas d'intervention sur place."}
                )
        images = attrs.get("images", [])
        if any(image.size > 5 * 1024 * 1024 for image in images):
            raise serializers.ValidationError(
                {"images": "Chaque photo doit faire 5 Mo maximum."}
            )
        return attrs

    def create(self, validated_data):
        images = validated_data.pop("images", [])
        quote = QuoteRequest.objects.create(
            customer=self.context["request"].user, **validated_data
        )
        QuoteAttachment.objects.bulk_create(
            [QuoteAttachment(quote=quote, image=image) for image in images]
        )
        return quote
