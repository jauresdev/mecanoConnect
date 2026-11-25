from rest_framework.routers import DefaultRouter

from .views import (
    AppointmentViewSet,
    CustomerVehicleViewSet,
    NotificationViewSet,
    QuoteReportViewSet,
    QuoteRequestViewSet,
    RepairShopViewSet,
    ReviewViewSet,
    ServiceViewSet,
    VehicleTypeViewSet,
)


router = DefaultRouter()
router.register("services", ServiceViewSet, basename="service")
router.register("vehicle-types", VehicleTypeViewSet, basename="vehicle-type")
router.register("shops", RepairShopViewSet, basename="shop")
router.register("vehicles", CustomerVehicleViewSet, basename="customer-vehicle")
router.register("quotes", QuoteRequestViewSet, basename="quote")
router.register("appointments", AppointmentViewSet, basename="appointment")
router.register("notifications", NotificationViewSet, basename="notification")
router.register("reports", QuoteReportViewSet, basename="quote-report")
router.register("reviews", ReviewViewSet, basename="review")

urlpatterns = router.urls
