import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateDocumentStorage(FileSystemStorage):
    def __init__(self):
        super().__init__(location=settings.PRIVATE_MEDIA_ROOT)

    def deconstruct(self):
        return ("apps.accounts.models.PrivateDocumentStorage", (), {})

    def url(self, name):
        raise ValueError("Les justificatifs professionnels ne sont pas publics.")


def verification_document_path(instance, filename):
    extension = filename.rsplit(".", 1)[-1].lower()
    return (
        f"verification/{instance.verification_id}/"
        f"{uuid.uuid4().hex}.{extension}"
    )


class User(AbstractUser):

    class Role(models.TextChoices):
        CUSTOMER = "customer", "Client"
        MECHANIC = "mechanic", "Réparateur"

    class VehicleScope(models.TextChoices):
        AUTO = "auto", "Automobile"
        MOTO = "moto", "Moto"
        BOTH = "both", "Automobile et moto"

    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True, validators=[])
    phone = models.CharField(max_length=32, blank=True)

    role = models.CharField(
        max_length=16,
        choices=Role.choices,
        default=Role.CUSTOMER
    )

    profile_photo = models.ImageField(
        upload_to="profiles/",
        blank=True
    )

    vehicle_scope = models.CharField(
        max_length=8,
        choices=VehicleScope.choices,
        blank=True
    )

    def __str__(self):
        return self.email


class ProfessionalVerification(models.Model):

    class Status(models.TextChoices):
        NOT_SUBMITTED = "not_submitted", "Non soumis"
        PENDING = "pending", "En attente"
        IN_REVIEW = "in_review", "En cours de vérification"
        VERIFIED = "verified", "Vérifié"
        REJECTED = "rejected", "Refusé"

    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="verification_submissions"
    )

    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING
    )

    rejection_reason = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_verifications"
    )

    class Meta:
        ordering = ("-submitted_at", "-id")
        indexes = [
            models.Index(fields=("status", "submitted_at"))
        ]

    def __str__(self):
        return (
            f"Vérification de {self.user.username} "
            f"({self.get_status_display()})"
        )


class VerificationDocument(models.Model):

    class DocumentType(models.TextChoices):
        IDENTITY = "identity", "Pièce d’identité"
        TRAINING = "training", "Formation ou diplôme"
        BUSINESS = "business", "Justificatif d’activité"
        OTHER = "other", "Autre document"

    verification = models.ForeignKey(
        ProfessionalVerification,
        on_delete=models.CASCADE,
        related_name="documents"
    )

    document_type = models.CharField(
        max_length=16,
        choices=DocumentType.choices
    )

    file = models.FileField(
        upload_to=verification_document_path,
        storage=PrivateDocumentStorage()
    )

    original_filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("uploaded_at", "id")

    def __str__(self):
        return (
            f"{self.get_document_type_display()} — "
            f"{self.verification.user.username}"
        )


class VerificationDecision(models.Model):

    verification = models.ForeignKey(
        ProfessionalVerification,
        on_delete=models.CASCADE,
        related_name="decisions"
    )

    previous_status = models.CharField(max_length=16)

    new_status = models.CharField(
        max_length=16,
        choices=ProfessionalVerification.Status.choices
    )

    reason = models.TextField(blank=True)

    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="verification_decisions"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "id")

    def __str__(self):
        return f"{self.previous_status} → {self.new_status}"