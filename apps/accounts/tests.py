from io import BytesIO
import tempfile
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory
from PIL import Image
from rest_framework.test import APITestCase

from apps.marketplace.models import Notification, RepairShop
from .admin import (
    CustomUserAdmin,
    ProfessionalVerificationAdmin,
    VerificationAdminForm,
)
from .models import (
    ProfessionalVerification,
    PrivateDocumentStorage,
    VerificationDecision,
    VerificationDocument,
)


User = get_user_model()


class AccountApiTests(APITestCase):
    def test_registration_hashes_password_and_returns_customer_role(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "new-client",
                "email": "client@example.com",
                "password": "ClientPass123!secure",
                "role": "customer",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        user = User.objects.get(username="new-client")
        self.assertTrue(user.check_password("ClientPass123!secure"))
        self.assertEqual(response.data["role"], User.Role.CUSTOMER)

    def test_registration_cannot_create_admin_account(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "admin-attempt",
                "email": "admin-attempt@example.com",
                "password": "ClientPass123!secure",
                "role": "admin",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(username="admin-attempt").exists())

    def test_mechanic_registration_requires_a_vehicle_space(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "mechanic-without-space",
                "email": "mechanic-without-space@example.com",
                "password": "MechanicPass123!secure",
                "role": "mechanic",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(username="mechanic-without-space").exists())

        for scope in ("auto", "moto", "both"):
            with self.subTest(scope=scope):
                response = self.client.post(
                    "/api/auth/register/",
                    {
                        "username": f"{scope}-mechanic",
                        "email": f"{scope}-mechanic@example.com",
                        "password": "MechanicPass123!secure",
                        "role": "mechanic",
                        "vehicle_scope": scope,
                    },
                    format="json",
                )

                self.assertEqual(response.status_code, 201, response.data)
                self.assertEqual(response.data["vehicle_scope"], scope)


class ProfessionalVerificationApiTests(APITestCase):
    def setUp(self):
        self.mechanic = User.objects.create_user(
            username="verification-mechanic",
            email="verification-mechanic@example.com",
            password="MechanicPass123!secure",
            role=User.Role.MECHANIC,
            vehicle_scope=User.VehicleScope.BOTH,
        )
        self.customer = User.objects.create_user(
            username="verification-customer",
            email="verification-customer@example.com",
            password="CustomerPass123!secure",
            role=User.Role.CUSTOMER,
        )
        self.staff = User.objects.create_user(
            username="verification-staff",
            email="verification-staff@example.com",
            password="StaffPass123!secure",
            is_staff=True,
        )
        self.storage_directory = tempfile.TemporaryDirectory()
        self.storage_override = patch.object(
            VerificationDocument._meta.get_field("file"),
            "storage",
            FileSystemStorage(location=self.storage_directory.name),
        )
        self.storage_override.start()
        self.addCleanup(self.storage_override.stop)
        self.addCleanup(self.storage_directory.cleanup)

    def make_pdf(self, name):
        return SimpleUploadedFile(
            name,
            b"%PDF-1.4\nVerification evidence\n",
            content_type="application/pdf",
        )

    def submit_documents(self):
        return self.client.post(
            "/api/auth/verification/",
            {
                "identity_document": self.make_pdf("identity.pdf"),
                "business_document": self.make_pdf("business.pdf"),
            },
            format="multipart",
        )

    def create_shop(self):
        return RepairShop.objects.create(
            owner=self.mechanic,
            name="Atelier vérifié",
            business_type=RepairShop.BusinessType.GARAGE,
            city="Parakou",
            district="Banikanni",
            phone="+22960000000",
            publication_status=RepairShop.PublicationStatus.APPROVED,
        )

    def review(self, verification, status, reason=""):
        request = RequestFactory().post("/admin/accounts/professionalverification/")
        request.user = self.staff
        verification.status = status
        verification.rejection_reason = reason
        model_admin = ProfessionalVerificationAdmin(
            ProfessionalVerification, admin.site
        )
        with patch.object(model_admin, "message_user"):
            model_admin.save_model(request, verification, None, change=True)

    def test_mechanic_can_update_profile_without_changing_account_scope(self):
        self.client.force_authenticate(user=self.mechanic)

        response = self.client.patch(
            "/api/auth/me/",
            {
                "first_name": "Aïcha",
                "last_name": "Dossou",
                "phone": "+22961000000",
                "role": "customer",
                "vehicle_scope": "auto",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.mechanic.refresh_from_db()
        self.assertEqual(self.mechanic.first_name, "Aïcha")
        self.assertEqual(self.mechanic.last_name, "Dossou")
        self.assertEqual(self.mechanic.phone, "+22961000000")
        self.assertEqual(self.mechanic.role, User.Role.MECHANIC)
        self.assertEqual(self.mechanic.vehicle_scope, User.VehicleScope.BOTH)

    def test_mechanic_can_upload_a_valid_profile_photo(self):
        image_buffer = BytesIO()
        Image.new("RGB", (4, 4), color="blue").save(image_buffer, format="PNG")
        image = SimpleUploadedFile(
            "profile.png", image_buffer.getvalue(), content_type="image/png"
        )
        self.client.force_authenticate(user=self.mechanic)

        with tempfile.TemporaryDirectory() as media_root:
            with self.settings(MEDIA_ROOT=media_root):
                response = self.client.patch(
                    "/api/auth/me/",
                    {"profile_photo": image},
                    format="multipart",
                )
                self.assertEqual(response.status_code, 200, response.data)
                self.mechanic.refresh_from_db()
                self.assertTrue(self.mechanic.profile_photo)
                self.assertTrue(
                    self.mechanic.profile_photo.path.startswith(media_root)
                )
                self.mechanic.profile_photo.delete(save=False)

    def test_mechanic_submission_validates_documents_and_owns_status(self):
        self.client.force_authenticate(user=self.mechanic)
        initial = self.client.get("/api/auth/verification/")
        self.assertEqual(initial.data["status"], ProfessionalVerification.Status.NOT_SUBMITTED)

        invalid = self.client.post(
            "/api/auth/verification/",
            {
                "identity_document": SimpleUploadedFile(
                    "identity.pdf", b"not a PDF", content_type="application/pdf"
                ),
                "business_document": self.make_pdf("business.pdf"),
            },
            format="multipart",
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertFalse(ProfessionalVerification.objects.exists())

        response = self.client.post(
            "/api/auth/verification/",
            {
                "identity_document": self.make_pdf("identity.pdf"),
                "business_document": self.make_pdf("business.pdf"),
                "training_document": self.make_pdf("training.pdf"),
                "other_documents": [
                    self.make_pdf("workshop.pdf"),
                    self.make_pdf("certificate.pdf"),
                ],
                "status": ProfessionalVerification.Status.VERIFIED,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["status"], ProfessionalVerification.Status.PENDING)
        self.assertEqual(len(response.data["documents"]), 5)
        self.assertNotIn("file", response.data["documents"][0])
        self.assertEqual(
            VerificationDocument.objects.filter(
                verification__user=self.mechanic
            ).count(),
            5,
        )
        self.assertEqual(
            VerificationDecision.objects.filter(
                verification__user=self.mechanic
            ).count(),
            1,
        )
        self.assertEqual(
            self.client.patch(
                "/api/auth/verification/",
                {"status": ProfessionalVerification.Status.VERIFIED},
                format="json",
            ).status_code,
            405,
        )
        duplicate = self.submit_documents()
        self.assertEqual(duplicate.status_code, 400)

    def test_non_mechanic_cannot_submit_verification(self):
        self.client.force_authenticate(user=self.customer)
        response = self.submit_documents()
        self.assertEqual(response.status_code, 403)
        self.assertFalse(ProfessionalVerification.objects.exists())

    def test_only_authorized_staff_can_download_private_documents(self):
        self.client.force_authenticate(user=self.mechanic)
        submitted = self.submit_documents()
        self.assertEqual(submitted.status_code, 201)
        document = VerificationDocument.objects.get(
            verification_id=submitted.data["id"],
            document_type=VerificationDocument.DocumentType.IDENTITY,
        )
        self.assertTrue(document.file.path.startswith(self.storage_directory.name))
        with self.assertRaises(ValueError):
            PrivateDocumentStorage().url(document.file.name)
        public_response = self.client.get(f"/media/{document.file.name}")
        self.assertEqual(public_response.status_code, 404)

        self.client.force_authenticate(user=None)
        self.client.force_login(self.customer)
        denied = self.client.get(
            f"/api/auth/verification/documents/{document.id}/download/"
        )
        self.assertEqual(denied.status_code, 403)
        self.client.logout()

        self.client.force_login(self.staff)
        staff_denied = self.client.get(
            f"/api/auth/verification/documents/{document.id}/download/"
        )
        self.assertEqual(staff_denied.status_code, 403)

        self.staff.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="accounts",
                codename="view_professionalverification",
            ),
            Permission.objects.get(
                content_type__app_label="accounts",
                codename="view_verificationdocument",
            ),
        )
        admin_page = self.client.get("/admin/accounts/professionalverification/")
        self.assertEqual(admin_page.status_code, 200)
        allowed = self.client.get(
            f"/api/auth/verification/documents/{document.id}/download/"
        )
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(allowed["X-Content-Type-Options"], "nosniff")
        self.assertIn("no-store", allowed["Cache-Control"])
        self.assertIn(b"%PDF-1.4", b"".join(allowed.streaming_content))
        allowed.close()

    def test_admin_decisions_control_badges_and_keep_latest_submission_authoritative(self):
        shop = self.create_shop()
        self.assertFalse(shop.is_verified)
        public_profile = self.client.get(f"/api/shops/{shop.id}/")
        self.assertEqual(public_profile.status_code, 200)
        self.assertFalse(public_profile.data["is_verified"])

        older = ProfessionalVerification.objects.create(
            user=self.mechanic,
            status=ProfessionalVerification.Status.PENDING,
        )
        self.review(older, ProfessionalVerification.Status.VERIFIED)
        shop.refresh_from_db()
        self.assertTrue(shop.is_verified)
        self.assertEqual(older.reviewed_by, self.staff)
        public_profile = self.client.get(f"/api/shops/{shop.id}/")
        self.assertTrue(public_profile.data["is_verified"])

        self.review(
            older,
            ProfessionalVerification.Status.REJECTED,
            "Les justificatifs doivent être actualisés.",
        )
        shop.refresh_from_db()
        self.assertFalse(shop.is_verified)

        rejection_form = VerificationAdminForm(
            {
                "status": ProfessionalVerification.Status.REJECTED,
                "rejection_reason": "",
            },
            instance=older,
        )
        self.assertFalse(rejection_form.is_valid())

        self.client.force_authenticate(user=self.mechanic)
        resubmission = self.submit_documents()
        self.assertEqual(resubmission.status_code, 201, resubmission.data)
        latest = ProfessionalVerification.objects.get(pk=resubmission.data["id"])
        self.client.force_authenticate(user=None)

        self.review(older, ProfessionalVerification.Status.PENDING)
        self.review(older, ProfessionalVerification.Status.VERIFIED)
        shop.refresh_from_db()
        self.assertFalse(shop.is_verified)

        self.review(
            latest,
            ProfessionalVerification.Status.REJECTED,
            "Justificatif d’activité illisible.",
        )
        latest.refresh_from_db()
        self.assertEqual(
            latest.rejection_reason,
            "Justificatif d’activité illisible.",
        )
        self.review(
            latest,
            ProfessionalVerification.Status.VERIFIED,
        )
        shop.refresh_from_db()
        self.assertTrue(shop.is_verified)
        public_profile = self.client.get(f"/api/shops/{shop.id}/")
        self.assertTrue(public_profile.data["is_verified"])
        self.assertEqual(
            VerificationDecision.objects.filter(
                verification=latest,
                new_status=ProfessionalVerification.Status.REJECTED,
                reason="Justificatif d’activité illisible.",
            ).count(),
            1,
        )

    def test_latest_verification_decisions_notify_the_mechanic(self):
        verification = ProfessionalVerification.objects.create(
            user=self.mechanic,
            status=ProfessionalVerification.Status.PENDING,
        )

        self.review(
            verification,
            ProfessionalVerification.Status.REJECTED,
            "La pièce d’identité est illisible.",
        )

        notification = Notification.objects.get(recipient=self.mechanic)
        self.assertEqual(
            notification.event,
            "professional_verification_rejected",
        )
        self.assertIn("La pièce d’identité est illisible.", notification.message)
        self.assertIsNone(notification.quote)

        self.review(
            verification,
            ProfessionalVerification.Status.REJECTED,
            "La pièce d’identité est illisible.",
        )
        self.assertEqual(Notification.objects.filter(recipient=self.mechanic).count(), 1)

    def test_admin_can_suspend_and_reactivate_a_verified_mechanic(self):
        shop = self.create_shop()
        verification = ProfessionalVerification.objects.create(
            user=self.mechanic,
            status=ProfessionalVerification.Status.PENDING,
        )
        self.review(verification, ProfessionalVerification.Status.VERIFIED)
        shop.refresh_from_db()
        self.assertTrue(shop.is_verified)

        request = RequestFactory().post("/admin/accounts/user/")
        request.user = self.staff
        user_admin = CustomUserAdmin(User, admin.site)
        self.mechanic.is_active = False
        user_admin.save_model(request, self.mechanic, None, change=True)

        shop.refresh_from_db()
        self.assertFalse(shop.is_verified)
        self.assertEqual(
            self.client.get(f"/api/shops/{shop.id}/").status_code,
            404,
        )

        self.mechanic.is_active = True
        user_admin.save_model(request, self.mechanic, None, change=True)
        shop.refresh_from_db()
        self.assertTrue(shop.is_verified)


class AdminDashboardTests(APITestCase):
    def test_sidebar_shows_useful_admin_features_in_french(self):
        staff = User.objects.create_user(
            username="sidebar-staff",
            email="sidebar-staff@example.com",
            password="StaffPass123!secure",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(staff)

        response = self.client.get("/admin/accounts/user/")

        self.assertEqual(response.status_code, 200)
        for label in (
            "Comptes utilisateurs",
            "Vérifications professionnelles",
            "Ateliers",
            "Demandes d’intervention",
            "Devis",
            "Signalements",
            "Rendez-vous",
            "Avis clients",
        ):
            self.assertContains(response, label)
        for hidden_label in (
            "Professional verifications",
            "Quote events",
            "Authentification et autorisation",
        ):
            self.assertNotContains(response, hidden_label)

    def test_staff_dashboard_shows_moderation_queues(self):
        staff = User.objects.create_user(
            username="dashboard-staff",
            email="dashboard-staff@example.com",
            password="StaffPass123!secure",
            is_staff=True,
            is_superuser=True,
        )
        mechanic = User.objects.create_user(
            username="dashboard-mechanic",
            email="dashboard-mechanic@example.com",
            password="MechanicPass123!secure",
            role=User.Role.MECHANIC,
        )
        ProfessionalVerification.objects.create(
            user=mechanic,
            status=ProfessionalVerification.Status.PENDING,
        )
        RepairShop.objects.create(
            owner=mechanic,
            name="Atelier en attente",
            business_type=RepairShop.BusinessType.GARAGE,
            city="Parakou",
            district="Banikanni",
            phone="+22960000000",
            publication_status=RepairShop.PublicationStatus.PENDING,
        )

        self.client.force_login(staff)
        response = self.client.get("/admin/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["pending_verifications"], 1)
        self.assertEqual(response.context["shops_pending_review"], 1)
        self.assertContains(response, "CENTRE DE PILOTAGE")
        self.assertContains(response, "status__exact=pending")
        self.assertContains(response, "dashboard-mechanic")
        self.assertContains(response, "Atelier en attente")

    def test_admin_login_uses_the_mecanoconnect_admin_brand(self):
        response = self.client.get("/admin/login/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ESPACE D’ADMINISTRATION")
        self.assertContains(response, "Nom d’utilisateur")
        self.assertContains(response, "Mot de passe")
        self.assertContains(response, "Admin")
        self.assertNotContains(response, "Administration de Django")

    def test_non_staff_cannot_access_the_admin_dashboard(self):
        customer = User.objects.create_user(
            username="dashboard-customer",
            email="dashboard-customer@example.com",
            password="CustomerPass123!secure",
            role=User.Role.CUSTOMER,
        )
        self.client.force_login(customer)

        response = self.client.get("/admin/")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])
