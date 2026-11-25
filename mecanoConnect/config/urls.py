from django.contrib import admin
from django.conf import settings
from django.urls import include, path
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)
from rest_framework import serializers
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


class HealthCheckSerializer(serializers.Serializer):
    status = serializers.CharField()


class HealthCheckView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = HealthCheckSerializer

    def get(self, request):
        return Response(self.get_serializer({"status": "ok"}).data)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", HealthCheckView.as_view(), name="health"),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/", include("apps.marketplace.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
