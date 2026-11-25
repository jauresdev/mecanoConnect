from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Service(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class VehicleType(models.Model):
    name = models.CharField(max_length=40, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class RepairShop(models.Model):
    class BusinessType(models.TextChoices):
        GARAGE = "garage", "Garage"
        MECHANIC = "mechanic", "Mécanicien"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="repair_shops",
    )
    name = models.CharField(max_length=160)
    business_type = models.CharField(max_length=16, choices=BusinessType.choices)
    description = models.TextField(max_length=3000, blank=True)
    city = models.CharField(max_length=100, default="Parakou")
    district = models.CharField(max_length=100)
    address = models.CharField(max_length=250, blank=True)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    phone = models.CharField(max_length=32)
    whatsapp = models.CharField(max_length=32, blank=True)
    photo = models.ImageField(upload_to="shops/", blank=True)
    services = models.ManyToManyField(Service, related_name="repair_shops", blank=True)
    vehicle_types = models.ManyToManyField(
        VehicleType, related_name="repair_shops", blank=True
    )
    mobile_service = models.BooleanField(default=False)
    opening_hours = models.JSONField(default=dict, blank=True)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        indexes = [
            models.Index(fields=("city", "district")),
            models.Index(fields=("is_active", "is_verified")),
        ]

    def __str__(self):
        return self.name


class QuoteRequest(models.Model):
    class Urgency(models.TextChoices):
        IMMEDIATE = "immediate", "Immédiate"
        PLANNED = "planned", "Planifiée"

    class Status(models.TextChoices):
        NEW = "new", "Nouvelle"
        ANSWERED = "answered", "Répondue"
        ACCEPTED = "accepted", "Acceptée"
        IN_PROGRESS = "in_progress", "En cours"
        DECLINED = "declined", "Refusée"
        COMPLETED = "completed", "Terminée"
        CANCELLED = "cancelled", "Annulée"

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="quote_requests",
    )
    shop = models.ForeignKey(
        RepairShop,
        on_delete=models.PROTECT,
        related_name="quote_requests",
    )
    vehicle_type = models.ForeignKey(
        VehicleType, on_delete=models.PROTECT, related_name="quote_requests"
    )
    vehicle_model = models.CharField(max_length=120)
    problem = models.TextField(max_length=3000)
    urgency = models.CharField(max_length=16, choices=Urgency.choices)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.NEW
    )
    mechanic_response = models.TextField(max_length=3000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("shop", "status", "created_at"))]

    def __str__(self):
        return f"Devis #{self.pk} — {self.shop.name}"


class Review(models.Model):
    shop = models.ForeignKey(
        RepairShop, on_delete=models.CASCADE, related_name="reviews"
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews"
    )
    rating = models.PositiveSmallIntegerField(
        validators=(MinValueValidator(1), MaxValueValidator(5))
    )
    comment = models.TextField(max_length=1500, blank=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("shop", "customer"), name="unique_review_per_customer_shop"
            )
        ]
        indexes = [models.Index(fields=("shop", "is_approved"))]

    def __str__(self):
        return f"Avis {self.rating}/5 — {self.shop.name}"
