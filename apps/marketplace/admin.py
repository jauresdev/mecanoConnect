from django import forms
from django.contrib import admin
from django.db import transaction
from django.utils import timezone

from .models import (
    Appointment,
    CustomerVehicle,
    Notification,
    QuoteEvent,
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
from .workflows import record_quote_event


@admin.register(RepairShop)
class RepairShopAdmin(admin.ModelAdmin):
    class Form(forms.ModelForm):
        class Meta:
            model = RepairShop
            fields = "__all__"

        def clean(self):
            cleaned_data = super().clean()
            if (
                cleaned_data.get("publication_status")
                == RepairShop.PublicationStatus.REJECTED
                and not (cleaned_data.get("publication_review_note") or "").strip()
            ):
                self.add_error(
                    "publication_review_note",
                    "Indiquez les modifications attendues du mécanicien.",
                )
            return cleaned_data

    form = Form
    list_display = (
        "name",
        "owner",
        "city",
        "district",
        "publication_status",
        "is_verified",
        "is_active",
    )
    list_filter = (
        "business_type",
        "publication_status",
        "city",
        "is_verified",
        "is_active",
    )
    search_fields = ("name", "owner__email", "district", "city")
    filter_horizontal = ("services", "vehicle_types")
    readonly_fields = (
        "is_verified",
        "publication_reviewed_at",
        "publication_reviewed_by",
        "created_at",
        "updated_at",
    )

    def save_model(self, request, obj, form, change):
        previous_status = None
        if change:
            previous_status = RepairShop.objects.get(pk=obj.pk).publication_status
        if change and previous_status != obj.publication_status:
            obj.publication_reviewed_at = timezone.now()
            obj.publication_reviewed_by = request.user
        super().save_model(request, obj, form, change)
        if change and previous_status != obj.publication_status:
            notification = {
                RepairShop.PublicationStatus.APPROVED: (
                    "repair_shop_approved",
                    f"Votre atelier « {obj.name} » a été approuvé et publié.",
                ),
                RepairShop.PublicationStatus.REJECTED: (
                    "repair_shop_changes_requested",
                    (
                        f"Des modifications sont demandées pour votre atelier "
                        f"« {obj.name} ». Motif : {obj.publication_review_note}"
                    ),
                ),
            }.get(obj.publication_status)
            if notification:
                Notification.objects.create(
                    recipient=obj.owner,
                    event=notification[0],
                    message=notification[1],
                )


@admin.register(QuoteRequest)
class QuoteRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "shop", "customer", "status", "category", "urgency", "created_at")
    list_filter = ("status", "category", "urgency", "created_at")
    search_fields = ("shop__name", "customer__email", "vehicle_model")
    readonly_fields = (
        "customer",
        "shop",
        "vehicle_type",
        "vehicle",
        "vehicle_model",
        "problem",
        "urgency",
        "category",
        "location",
        "service_mode",
        "availability",
        "status",
        "mechanic_response",
        "refusal_reason",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(QuoteEvent)
class QuoteEventAdmin(admin.ModelAdmin):
    list_display = ("quote", "action", "actor", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("quote__shop__name", "quote__customer__email", "details")
    readonly_fields = ("quote", "actor", "action", "details", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(QuoteReport)
class QuoteReportAdmin(admin.ModelAdmin):
    list_display = ("quote", "reporter", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("quote__shop__name", "reporter__email", "reason")
    readonly_fields = ("quote", "reporter", "reason", "status", "created_at")
    actions = ("resolve_reports",)

    def has_add_permission(self, request):
        return False

    @admin.action(description="Marquer les signalements sélectionnés comme résolus")
    def resolve_reports(self, request, queryset):
        with transaction.atomic():
            for report in queryset.exclude(status=QuoteReport.Status.RESOLVED):
                report.status = QuoteReport.Status.RESOLVED
                report.save(update_fields=("status",))
                record_quote_event(
                    report.quote,
                    request.user,
                    "report_resolved",
                    "L'administration a traité le signalement.",
                    report.reporter,
                )

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(QuoteOffer)
class QuoteOfferAdmin(admin.ModelAdmin):
    list_display = ("quote", "version", "status", "labor_cost", "travel_cost", "created_at")
    list_filter = ("status", "created_at")
    readonly_fields = (
        "quote",
        "version",
        "description",
        "labor_cost",
        "travel_cost",
        "estimated_duration_minutes",
        "valid_until",
        "conditions",
        "currency",
        "is_supplemental",
        "resume_status",
        "status",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("quote", "scheduled_at", "status", "proposed_by")
    list_filter = ("status", "scheduled_at")
    readonly_fields = (
        "quote",
        "proposed_by",
        "scheduled_at",
        "duration_minutes",
        "status",
        "note",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CustomerVehicle)
class CustomerVehicleAdmin(admin.ModelAdmin):
    list_display = ("customer", "vehicle_type", "make", "model", "year")
    search_fields = ("customer__email", "make", "model", "registration")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient", "event", "is_read", "created_at")
    list_filter = ("event", "is_read", "created_at")
    readonly_fields = ("recipient", "quote", "event", "message", "created_at")

    def has_add_permission(self, request):
        return False


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("shop", "customer", "rating", "is_approved", "created_at")
    list_filter = ("is_approved", "rating", "created_at")
    search_fields = ("shop__name", "customer__email", "comment")
    actions = ("approve_reviews", "hide_reviews")

    @admin.action(description="Approuver les avis sélectionnés")
    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)

    @admin.action(description="Masquer les avis sélectionnés")
    def hide_reviews(self, request, queryset):
        queryset.update(is_approved=False)


admin.site.register(Service)
admin.site.register(VehicleType)


@admin.register(QuotePart)
class QuotePartAdmin(admin.ModelAdmin):
    list_display = ("offer", "name", "quantity", "unit_price")
    readonly_fields = ("offer", "name", "quantity", "unit_price")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(RepairShopPhoto)
class RepairShopPhotoAdmin(admin.ModelAdmin):
    list_display = ("shop", "created_at")
    search_fields = ("shop__name",)
    readonly_fields = ("created_at",)
