from rest_framework.routers import DefaultRouter

from .views import (
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
router.register("quotes", QuoteRequestViewSet, basename="quote")
router.register("reviews", ReviewViewSet, basename="review")

urlpatterns = router.urls
