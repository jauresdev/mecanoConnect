from datetime import time

from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import QuoteRequest, RepairShop, Review, Service, VehicleType


User = get_user_model()


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ("id", "name", "slug")


class VehicleTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleType
        fields = ("id", "name", "slug")


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
        many=True, queryset=Service.objects.filter(is_active=True), required=False
    )
    vehicle_types = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=VehicleType.objects.filter(is_active=True),
        required=False,
    )
    owner_name = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()

    class Meta:
        model = RepairShop
        fields = (
            "id",
            "owner",
            "owner_name",
            "name",
            "business_type",
            "description",
            "city",
            "district",
            "address",
            "latitude",
            "longitude",
            "phone",
            "whatsapp",
            "photo",
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
            "is_verified",
            "average_rating",
            "review_count",
            "created_at",
            "updated_at",
        )

    def validate_photo(self, photo):
        if photo and photo.size > 5 * 1024 * 1024:
            raise serializers.ValidationError(
                "La photo ne peut pas dépasser 5 Mo."
            )
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
        return attrs


class QuoteRequestSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()
    shop_name = serializers.CharField(source="shop.name", read_only=True)

    class Meta:
        model = QuoteRequest
        fields = (
            "id",
            "customer",
            "customer_name",
            "shop",
            "shop_name",
            "vehicle_type",
            "vehicle_model",
            "problem",
            "urgency",
            "status",
            "mechanic_response",
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
            "created_at",
            "updated_at",
        )

    @extend_schema_field(serializers.CharField())
    def get_customer_name(self, quote):
        return quote.customer.get_full_name() or quote.customer.username

    def validate(self, attrs):
        request = self.context["request"]
        if request.method == "POST":
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
        return attrs

    def create(self, validated_data):
        return QuoteRequest.objects.create(
            customer=self.context["request"].user, **validated_data
        )
