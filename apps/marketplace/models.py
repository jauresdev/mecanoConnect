from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateQuoteStorage(FileSystemStorage):
    def __init__(self):
        super().__init__(location=settings.BASE_DIR / "private_uploads")


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


class CustomerVehicle(models.Model):
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="vehicles",
    )
    vehicle_type = models.ForeignKey(
        VehicleType, on_delete=models.PROTECT, related_name="customer_vehicles"
    )
    make = models.CharField(max_length=80)
    model = models.CharField(max_length=120)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    registration = models.CharField(max_length=24, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("make", "model", "id")

    def __str__(self):
        return f"{self.make} {self.model}"


class QuoteRequest(models.Model):
    class Urgency(models.TextChoices):
        IMMEDIATE = "immediate", "Immédiate"
        PLANNED = "planned", "Planifiée"

    class Category(models.TextChoices):
        ENGINE = "engine", "Panne moteur"
        ELECTRICAL = "electrical", "Problème électrique"
        BRAKES = "brakes", "Freinage"
        BATTERY = "battery", "Batterie"
        TIRES = "tires", "Pneumatique"
        MAINTENANCE = "maintenance", "Entretien"
        ACCIDENT = "accident", "Accident"
        OTHER = "other", "Autre problème"

    class ServiceMode(models.TextChoices):
        WORKSHOP = "workshop", "En atelier"
        ON_SITE = "on_site", "Sur place"

    class Status(models.TextChoices):
        NEW = "new", "Nouvelle"
        ANSWERED = "answered", "Répondue"
        DISCUSSION = "discussion", "En discussion"
        DECLINED = "declined", "Refusée"
        QUOTE_SENT = "quote_sent", "Devis envoyé"
        QUOTE_ACCEPTED = "quote_accepted", "Devis accepté"
        QUOTE_DECLINED = "quote_declined", "Devis refusé"
        APPOINTMENT_CONFIRMED = "appointment_confirmed", "Rendez-vous confirmé"
        ACCEPTED = "accepted", "Acceptée"
        IN_PROGRESS = "in_progress", "En cours"
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
    vehicle = models.ForeignKey(
        CustomerVehicle,
        on_delete=models.SET_NULL,
        related_name="quote_requests",
        null=True,
        blank=True,
    )
    vehicle_model = models.CharField(max_length=120)
    problem = models.TextField(max_length=3000)
    urgency = models.CharField(max_length=16, choices=Urgency.choices)
    category = models.CharField(
        max_length=16, choices=Category.choices, default=Category.OTHER
    )
    location = models.CharField(max_length=250, blank=True)
    service_mode = models.CharField(
        max_length=12, choices=ServiceMode.choices, default=ServiceMode.WORKSHOP
    )
    availability = models.TextField(max_length=1000, blank=True)
    refusal_reason = models.CharField(max_length=1000, blank=True)
    status = models.CharField(
        max_length=24, choices=Status.choices, default=Status.NEW
    )
    mechanic_response = models.TextField(max_length=3000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("shop", "status", "created_at"))]

    def __str__(self):
        return f"Devis #{self.pk} — {self.shop.name}"


class QuoteAttachment(models.Model):
    quote = models.ForeignKey(
        QuoteRequest, on_delete=models.CASCADE, related_name="attachments"
    )
    image = models.ImageField(
        storage=PrivateQuoteStorage(), upload_to="quote-attachments/"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "id")


class QuoteMessage(models.Model):
    quote = models.ForeignKey(
        QuoteRequest, on_delete=models.CASCADE, related_name="messages"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="quote_messages",
    )
    message = models.TextField(max_length=3000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "id")


class QuoteOffer(models.Model):
    class Status(models.TextChoices):
        SENT = "sent", "Envoyé"
        ACCEPTED = "accepted", "Accepté"
        DECLINED = "declined", "Refusé"
        CHANGE_REQUESTED = "change_requested", "Modification demandée"
        SUPERSEDED = "superseded", "Remplacé"

    quote = models.ForeignKey(
        QuoteRequest, on_delete=models.CASCADE, related_name="offers"
    )
    version = models.PositiveIntegerField()
    description = models.TextField(max_length=3000)
    labor_cost = models.DecimalField(max_digits=12, decimal_places=0)
    travel_cost = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    estimated_duration_minutes = models.PositiveIntegerField()
    valid_until = models.DateField()
    conditions = models.TextField(max_length=2000, blank=True)
    currency = models.CharField(max_length=3, default="XOF", editable=False)
    is_supplemental = models.BooleanField(default=False)
    resume_status = models.CharField(max_length=24, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.SENT
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-version",)
        constraints = [
            models.UniqueConstraint(
                fields=("quote", "version"), name="unique_quote_offer_version"
            )
        ]

    @property
    def total(self):
        parts_total = sum(
            (part.quantity * part.unit_price for part in self.parts.all()), start=0
        )
        return self.labor_cost + self.travel_cost + parts_total


class QuotePart(models.Model):
    offer = models.ForeignKey(
        QuoteOffer, on_delete=models.CASCADE, related_name="parts"
    )
    name = models.CharField(max_length=160)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=0)


class Appointment(models.Model):
    class Status(models.TextChoices):
        PROPOSED = "proposed", "Proposé"
        CONFIRMED = "confirmed", "Confirmé"
        DECLINED = "declined", "Refusé"
        CANCELLED = "cancelled", "Annulé"

    quote = models.ForeignKey(
        QuoteRequest, on_delete=models.CASCADE, related_name="appointments"
    )
    proposed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="proposed_appointments",
    )
    scheduled_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField()
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.PROPOSED
    )
    note = models.CharField(max_length=1000, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("scheduled_at", "id")
        indexes = [models.Index(fields=("scheduled_at", "status"))]


class QuoteEvent(models.Model):
    quote = models.ForeignKey(
        QuoteRequest, on_delete=models.CASCADE, related_name="events"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="quote_events",
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=40)
    details = models.CharField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "id")


class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    quote = models.ForeignKey(
        QuoteRequest,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )
    event = models.CharField(max_length=40)
    message = models.CharField(max_length=500)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("recipient", "is_read", "created_at"))]


class QuoteReport(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "À traiter"
        REVIEWING = "reviewing", "En cours"
        RESOLVED = "resolved", "Résolu"

    quote = models.ForeignKey(
        QuoteRequest, on_delete=models.CASCADE, related_name="reports"
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="quote_reports",
    )
    reason = models.TextField(max_length=2000)
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.OPEN
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)


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
