from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    CurrentUserView,
    LoginView,
    ProfessionalVerificationView,
    RegisterView,
    download_verification_document,
)


urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("token/", LoginView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("me/", CurrentUserView.as_view(), name="current_user"),
    path("verification/", ProfessionalVerificationView.as_view(), name="verification"),
    path(
        "verification/documents/<int:document_id>/download/",
        download_verification_document,
        name="verification-document-download",
    ),
]
