from django.contrib import admin

from .models import QuoteRequest, RepairShop, Review, Service, VehicleType


@admin.register(RepairShop)
class RepairShopAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "city", "district", "is_verified", "is_active")
    list_filter = ("business_type", "city", "is_verified", "is_active")
    search_fields = ("name", "owner__email", "district", "city")
    filter_horizontal = ("services", "vehicle_types")
    readonly_fields = ("created_at", "updated_at")


@admin.register(QuoteRequest)
class QuoteRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "shop", "customer", "status", "urgency", "created_at")
    list_filter = ("status", "urgency", "created_at")
    search_fields = ("shop__name", "customer__email", "vehicle_model")
    readonly_fields = ("created_at", "updated_at")


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
