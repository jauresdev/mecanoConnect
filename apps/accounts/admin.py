from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from apps.marketplace.models import Notification

from .models import (
    ProfessionalVerification,
    User,
    VerificationDecision,
    VerificationDocument,
)
from .services import sync_professional_verification_badges


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("MécanoConnect", {"fields": ("phone", "role", "vehicle_scope", "profile_photo")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("MécanoConnect", {"fields": ("email", "phone", "role", "vehicle_scope")}),
    )
    list_display = ("username", "email", "role", "vehicle_scope", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active")

    def save_model(self, request, obj, form, change):
        was_active = (
            User.objects.filter(pk=obj.pk).values_list("is_active", flat=True).first()
            if change
            else obj.is_active
        )
        super().save_model(request, obj, form, change)
        if was_active != obj.is_active:
            sync_professional_verification_badges(obj)


class VerificationAdminForm(forms.ModelForm):
    status = forms.ChoiceField(
        choices=(
            (ProfessionalVerification.Status.PENDING, "En attente"),
            (ProfessionalVerification.Status.IN_REVIEW, "En cours de vérification"),
            (ProfessionalVerification.Status.VERIFIED, "Vérifié"),
            (ProfessionalVerification.Status.REJECTED, "Refusé"),
        )
    )

    class Meta:
        model = ProfessionalVerification
        fields = ("status", "rejection_reason")
        widgets = {"rejection_reason": forms.Textarea(attrs={"rows": 4})}

    def clean(self):
        cleaned_data = super().clean()
        if (
            cleaned_data.get("status") == ProfessionalVerification.Status.REJECTED
            and not cleaned_data.get("rejection_reason", "").strip()
        ):
            self.add_error("rejection_reason", "Un motif est obligatoire pour un refus.")
        return cleaned_data


class VerificationDocumentInline(admin.TabularInline):
    model = VerificationDocument
    fields = ("document_type", "original_filename", "uploaded_at", "secure_download")
    readonly_fields = fields
    extra = 0
    can_delete = False

    @admin.display(description="Accès sécurisé")
    def secure_download(self, document):
        url = reverse(
            "verification-document-download",
            kwargs={"document_id": document.pk},
        )
        return format_html('<a href="{}">Télécharger le justificatif</a>', url)

    def has_add_permission(self, request, obj=None):
        return False


class VerificationDecisionInline(admin.TabularInline):
    model = VerificationDecision
    fields = ("previous_status", "new_status", "reason", "actor", "created_at")
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ProfessionalVerification)
class ProfessionalVerificationAdmin(admin.ModelAdmin):
    form = VerificationAdminForm
    list_display = ("user", "status", "submitted_at", "reviewed_at", "reviewed_by")
    list_filter = ("status", "submitted_at")
    search_fields = ("user__username", "user__first_name", "user__last_name", "user__email")
    readonly_fields = ("user", "submitted_at", "reviewed_at", "reviewed_by")
    fields = ("user", "status", "rejection_reason", "submitted_at", "reviewed_at", "reviewed_by")
    inlines = (VerificationDocumentInline, VerificationDecisionInline)

    def save_model(self, request, obj, form, change):
        previous = ProfessionalVerification.objects.get(pk=obj.pk) if change else None
        previous_status = previous.status if previous else None
        previous_reason = previous.rejection_reason if previous else ""
        status_changed = change and previous_status != obj.status
        reason_changed = change and previous_reason != obj.rejection_reason
        if obj.status != ProfessionalVerification.Status.REJECTED:
            obj.rejection_reason = ""
        if status_changed or reason_changed:
            obj.reviewed_by = request.user
            obj.reviewed_at = timezone.now()
        super().save_model(request, obj, form, change)
        if status_changed or reason_changed:
            VerificationDecision.objects.create(
                verification=obj,
                previous_status=previous_status,
                new_status=obj.status,
                reason=obj.rejection_reason,
                actor=request.user,
            )
            sync_professional_verification_badges(obj.user)
            latest_verification_id = (
                ProfessionalVerification.objects.filter(user=obj.user)
                .values_list("pk", flat=True)
                .first()
            )
            if latest_verification_id == obj.pk:
                status_message = {
                    ProfessionalVerification.Status.PENDING: (
                        "Votre demande de vérification est en attente."
                    ),
                    ProfessionalVerification.Status.IN_REVIEW: (
                        "Votre demande de vérification est en cours d’examen."
                    ),
                    ProfessionalVerification.Status.VERIFIED: (
                        "Votre profil professionnel est maintenant vérifié."
                    ),
                    ProfessionalVerification.Status.REJECTED: (
                        "Votre demande de vérification a été refusée."
                    ),
                }.get(obj.status, "Le statut de votre vérification a été mis à jour.")
                if (
                    obj.status == ProfessionalVerification.Status.REJECTED
                    and obj.rejection_reason
                ):
                    status_message += f" Motif : {obj.rejection_reason}"
                Notification.objects.create(
                    recipient=obj.user,
                    event=f"professional_verification_{obj.status}",
                    message=status_message,
                )
            self.message_user(
                request,
                "La décision de vérification a été enregistrée.",
                messages.SUCCESS,
            )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
