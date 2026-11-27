from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import FileResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView

from config.file_validation import validate_verification_document

from .models import (
    ProfessionalVerification,
    VerificationDecision,
    VerificationDocument,
    User,
)
from .serializers import (
    ProfessionalVerificationSerializer,
    RegistrationSerializer,
    UserSerializer,
)


class RegisterView(generics.CreateAPIView):
    serializer_class = RegistrationSerializer
    permission_classes = [permissions.AllowAny]


class LoginView(TokenObtainPairView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"


class CurrentUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class ProfessionalVerificationView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = (permissions.IsAuthenticated,)

    def get_mechanic(self, request):
        if request.user.role != User.Role.MECHANIC:
            raise PermissionDenied("La vérification est réservée aux réparateurs.")
        return request.user

    def get(self, request):
        mechanic = self.get_mechanic(request)
        verification = (
            ProfessionalVerification.objects.filter(user=mechanic)
            .prefetch_related("documents")
            .first()
        )
        if verification is None:
            return Response({"status": ProfessionalVerification.Status.NOT_SUBMITTED})
        return Response(ProfessionalVerificationSerializer(verification).data)

    @transaction.atomic
    def post(self, request):
        mechanic = self.get_mechanic(request)
        # Lock the user row so two simultaneous submissions cannot both pass the check.
        User.objects.select_for_update().get(pk=mechanic.pk)
        latest = ProfessionalVerification.objects.filter(user=mechanic).first()
        if latest and latest.status in {
            ProfessionalVerification.Status.PENDING,
            ProfessionalVerification.Status.IN_REVIEW,
            ProfessionalVerification.Status.VERIFIED,
        }:
            raise ValidationError(
                {"status": "Une demande de vérification est déjà en cours ou validée."}
            )

        uploads = [
            (VerificationDocument.DocumentType.IDENTITY, request.FILES.get("identity_document")),
            (VerificationDocument.DocumentType.BUSINESS, request.FILES.get("business_document")),
        ]
        if request.FILES.get("training_document"):
            uploads.append(
                (VerificationDocument.DocumentType.TRAINING, request.FILES["training_document"])
            )
        other_documents = request.FILES.getlist("other_documents")
        if len(other_documents) > 5:
            raise ValidationError(
                {"other_documents": "Vous pouvez joindre au maximum cinq documents annexes."}
            )
        uploads.extend((VerificationDocument.DocumentType.OTHER, upload) for upload in other_documents)

        if not uploads[0][1] or not uploads[1][1]:
            raise ValidationError(
                {
                    "documents": (
                        "Une pièce d’identité et un justificatif d’activité "
                        "sont obligatoires."
                    )
                }
            )
        if sum(upload.size for _, upload in uploads) > 30 * 1024 * 1024:
            raise ValidationError(
                {"documents": "La taille totale des documents ne peut pas dépasser 30 Mo."}
            )

        for _, upload in uploads:
            validate_verification_document(upload)

        verification = ProfessionalVerification.objects.create(
            user=mechanic,
            status=ProfessionalVerification.Status.PENDING,
        )
        for document_type, upload in uploads:
            original_filename = Path(upload.name.replace("\\", "/")).name[:255]
            VerificationDocument.objects.create(
                verification=verification,
                document_type=document_type,
                file=upload,
                original_filename=original_filename,
            )
        VerificationDecision.objects.create(
            verification=verification,
            previous_status=ProfessionalVerification.Status.NOT_SUBMITTED,
            new_status=ProfessionalVerification.Status.PENDING,
            actor=mechanic,
        )
        return Response(
            ProfessionalVerificationSerializer(verification).data,
            status=201,
        )


@login_required
def download_verification_document(request, document_id):
    if not (
        request.user.is_staff
        and request.user.has_perm("accounts.view_professionalverification")
        and request.user.has_perm("accounts.view_verificationdocument")
    ):
        return HttpResponseForbidden()
    document = get_object_or_404(
        VerificationDocument.objects.select_related("verification"),
        pk=document_id,
    )
    response = FileResponse(
        document.file.open("rb"),
        as_attachment=True,
        filename=document.original_filename,
        content_type="application/octet-stream",
    )
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response
