from io import BytesIO
import tempfile
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image
from rest_framework.test import APITestCase

from .models import (
    Appointment,
    CustomerVehicle,
    Notification,
    QuoteAttachment,
    QuoteOffer,
    QuoteRequest,
    RepairShop,
    Service,
    VehicleType,
)


User = get_user_model()


class MarketplaceApiTests(APITestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            username="client",
            email="client@example.com",
            password="ClientPass123!secure",
            role=User.Role.CUSTOMER,
        )
        self.mechanic = User.objects.create_user(
            username="mechanic",
            email="mechanic@example.com",
            password="MechanicPass123!secure",
            role=User.Role.MECHANIC,
        )
        self.other_mechanic = User.objects.create_user(
            username="other-mechanic",
            email="other@example.com",
            password="OtherPass123!secure",
            role=User.Role.MECHANIC,
        )
        self.moto, _ = VehicleType.objects.get_or_create(
            slug="moto", defaults={"name": "Moto"}
        )
        self.car, _ = VehicleType.objects.get_or_create(
            slug="voiture", defaults={"name": "Voiture"}
        )
        self.vidange, _ = Service.objects.get_or_create(
            slug="vidange", defaults={"name": "Vidange"}
        )
        self.shop = RepairShop.objects.create(
            owner=self.mechanic,
            name="Garage Banikanni",
            business_type=RepairShop.BusinessType.GARAGE,
            city="Parakou",
            district="Banikanni",
            phone="+22960000000",
        )
        self.shop.vehicle_types.add(self.moto, self.car)
        self.shop.services.add(self.vidange)

    def test_initial_catalogue_is_public(self):
        services = self.client.get("/api/services/")
        vehicles = self.client.get("/api/vehicle-types/")

        self.assertEqual(services.status_code, 200)
        self.assertEqual(vehicles.status_code, 200)
        self.assertTrue(
            any(item["slug"] == "diagnostic" for item in services.data["results"])
        )
        self.assertEqual(
            {item["slug"] for item in vehicles.data["results"]},
            {"moto", "voiture"},
        )

    def create_quote(self):
        return QuoteRequest.objects.create(
            customer=self.customer,
            shop=self.shop,
            vehicle_type=self.moto,
            vehicle_model="Honda CG 125",
            problem="Le moteur cale au ralenti.",
            urgency=QuoteRequest.Urgency.PLANNED,
        )

    def create_quote_via_api(self, vehicle_type=None):
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            "/api/quotes/",
            {
                "shop": self.shop.id,
                "vehicle_type": (vehicle_type or self.moto).id,
                "vehicle_model": "Honda CG 125",
                "problem": "Le moteur cale au ralenti.",
                "urgency": "planned",
                "category": "engine",
                "location": "Banikanni, Parakou",
                "service_mode": "workshop",
                "availability": "Après 15 h en semaine",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        return QuoteRequest.objects.get(pk=response.data["id"])

    def create_offer(self, quote, labor_cost="5000", parts=None):
        self.client.force_authenticate(self.mechanic)
        response = self.client.post(
            f"/api/quotes/{quote.id}/offers/",
            {
                "description": "Remplacement et réglage après diagnostic.",
                "total": "1",
                "parts": parts or [
                    {"name": "Filtre", "quantity": 2, "unit_price": "4000"}
                ],
                "labor_cost": labor_cost,
                "travel_cost": "1000",
                "estimated_duration_minutes": 120,
                "valid_until": (timezone.localdate() + timedelta(days=7)).isoformat(),
                "conditions": "Toute pièce supplémentaire fera l’objet d’un accord préalable.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        return response

    def test_mechanic_can_register_and_create_an_atelier(self):
        registration = self.client.post(
            "/api/auth/register/",
            {
                "username": "new-mechanic",
                "email": "new-mechanic@example.com",
                "password": "NewMechanicPass123!secure",
                "role": "mechanic",
            },
            format="json",
        )
        self.assertEqual(registration.status_code, 201)

        token = self.client.post(
            "/api/auth/token/",
            {
                "username": "new-mechanic",
                "password": "NewMechanicPass123!secure",
            },
            format="json",
        )
        self.assertEqual(token.status_code, 200)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {token.data['access']}"
        )

        created_shop = self.client.post(
            "/api/shops/",
            {
                "name": "Atelier de test",
                "business_type": "mechanic",
                "city": "Parakou",
                "district": "Zongo",
                "phone": "+22961000000",
                "services": [self.vidange.id],
                "vehicle_types": [self.moto.id],
            },
            format="json",
        )

        self.assertEqual(created_shop.status_code, 201)
        self.assertEqual(created_shop.data["owner"], registration.data["id"])
        self.assertEqual(created_shop.data["name"], "Atelier de test")

    def test_shop_owner_can_edit_shop_but_other_mechanic_cannot(self):
        self.client.force_authenticate(self.mechanic)
        updated = self.client.patch(
            f"/api/shops/{self.shop.id}/",
            {"name": "Garage Banikanni rénové", "district": "Zongo"},
            format="json",
        )

        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data["name"], "Garage Banikanni rénové")
        self.assertEqual(updated.data["district"], "Zongo")

        self.client.force_authenticate(self.other_mechanic)
        denied = self.client.patch(
            f"/api/shops/{self.shop.id}/",
            {"name": "Atelier usurpé"},
            format="json",
        )

        self.assertEqual(denied.status_code, 403)
        self.shop.refresh_from_db()
        self.assertEqual(self.shop.name, "Garage Banikanni rénové")

    def test_shop_owner_can_save_opening_hours_and_upload_a_photo(self):
        self.client.force_authenticate(self.mechanic)
        opening_hours = {
            "monday": {"open": "08:00", "close": "18:00"},
            "sunday": None,
        }
        updated = self.client.patch(
            f"/api/shops/{self.shop.id}/",
            {"opening_hours": opening_hours},
            format="json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data["opening_hours"], opening_hours)

        image_buffer = BytesIO()
        Image.new("RGB", (2, 2), color="green").save(image_buffer, format="PNG")
        image = SimpleUploadedFile(
            "atelier.png", image_buffer.getvalue(), content_type="image/png"
        )
        with tempfile.TemporaryDirectory() as media_root:
            with self.settings(MEDIA_ROOT=media_root):
                uploaded = self.client.patch(
                    f"/api/shops/{self.shop.id}/",
                    {"photo": image},
                    format="multipart",
                )
                self.assertEqual(uploaded.status_code, 200)
                self.assertTrue(uploaded.data["photo"].endswith(".png"))
                self.shop.refresh_from_db()
                self.assertTrue(self.shop.photo.name.startswith("shops/"))

    def test_shop_rejects_invalid_opening_hours(self):
        self.client.force_authenticate(self.mechanic)
        response = self.client.patch(
            f"/api/shops/{self.shop.id}/",
            {"opening_hours": {"monday": {"open": "18:00", "close": "08:00"}}},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_public_shop_search_filters_by_vehicle_service_and_district(self):
        response = self.client.get(
            "/api/shops/?vehicle=moto&service=vidange&district=banikanni"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Garage Banikanni")

    def test_customer_can_submit_quote_and_only_participants_can_read_it(self):
        self.client.force_authenticate(self.customer)
        create_response = self.client.post(
            "/api/quotes/",
            {
                "shop": self.shop.id,
                "vehicle_type": self.moto.id,
                "vehicle_model": "Honda CG 125",
                "problem": "Le moteur cale au ralenti.",
                "urgency": "planned",
            },
            format="json",
        )

        self.assertEqual(create_response.status_code, 201)
        quote_id = create_response.data["id"]

        self.client.force_authenticate(self.other_mechanic)
        hidden_response = self.client.get(f"/api/quotes/{quote_id}/")
        self.assertEqual(hidden_response.status_code, 404)

        self.client.force_authenticate(self.mechanic)
        visible_response = self.client.get(f"/api/quotes/{quote_id}/")
        self.assertEqual(visible_response.status_code, 200)
        mechanic_inbox = self.client.get("/api/quotes/")
        self.assertEqual(mechanic_inbox.status_code, 200)
        self.assertEqual(
            [item["id"] for item in mechanic_inbox.data["results"]],
            [quote_id],
        )

    def test_quote_workflow_and_review_moderation(self):
        quote = self.create_quote()
        self.client.force_authenticate(self.mechanic)
        answer = self.client.post(
            f"/api/quotes/{quote.id}/respond/",
            {"response": "Diagnostic possible demain matin."},
            format="json",
        )
        self.assertEqual(answer.status_code, 200)
        self.assertEqual(answer.data["status"], QuoteRequest.Status.ANSWERED)

        self.client.force_authenticate(self.customer)
        client_inbox = self.client.get("/api/quotes/")
        self.assertEqual(client_inbox.status_code, 200)
        self.assertEqual(client_inbox.data["results"][0]["mechanic_response"], "Diagnostic possible demain matin.")

        self.client.force_authenticate(self.customer)
        accepted = self.client.post(
            f"/api/quotes/{quote.id}/decide/",
            {"decision": "accepted"},
            format="json",
        )
        self.assertEqual(accepted.status_code, 200)

        self.client.force_authenticate(self.mechanic)
        started = self.client.post(
            f"/api/quotes/{quote.id}/start/", {}, format="json"
        )
        self.assertEqual(started.status_code, 200)
        self.assertEqual(started.data["status"], QuoteRequest.Status.IN_PROGRESS)
        completed = self.client.post(
            f"/api/quotes/{quote.id}/complete/", {}, format="json"
        )
        self.assertEqual(completed.data["status"], QuoteRequest.Status.COMPLETED)

        self.client.force_authenticate(self.customer)
        review = self.client.post(
            "/api/reviews/",
            {"shop": self.shop.id, "rating": 5, "comment": "Service sérieux."},
            format="json",
        )
        self.assertEqual(review.status_code, 201)
        self.assertTrue(review.data["is_mine"])
        self.assertFalse(review.data["is_approved"])
        self.assertFalse(self.shop.reviews.get(customer=self.customer).is_approved)

        own_reviews = self.client.get("/api/reviews/")
        self.assertTrue(own_reviews.data["results"][0]["is_mine"])

        public_reviews = self.client.get(f"/api/shops/{self.shop.id}/reviews/")
        self.assertEqual(public_reviews.data["count"], 0)

    def test_mechanic_cannot_reply_to_another_mechanics_quote(self):
        quote = self.create_quote()
        self.client.force_authenticate(self.other_mechanic)

        response = self.client.post(
            f"/api/quotes/{quote.id}/respond/",
            {"response": "Réponse non autorisée."},
            format="json",
        )

        self.assertEqual(response.status_code, 404)
        quote.refresh_from_db()
        self.assertEqual(quote.status, QuoteRequest.Status.NEW)

    def test_mechanic_response_rejects_non_object_payload(self):
        quote = self.create_quote()
        self.client.force_authenticate(self.mechanic)

        response = self.client.post(
            f"/api/quotes/{quote.id}/respond/",
            ["not", "an", "object"],
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_customer_cannot_request_unsupported_vehicle(self):
        unsupported_vehicle = VehicleType.objects.create(
            name="Camion", slug="camion"
        )
        self.client.force_authenticate(self.customer)

        response = self.client.post(
            "/api/quotes/",
            {
                "shop": self.shop.id,
                "vehicle_type": unsupported_vehicle.id,
                "vehicle_model": "Camion",
                "problem": "Problème moteur.",
                "urgency": "immediate",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_auto_and_moto_requests_are_owned_and_only_delivered_to_target_shop(self):
        other_shop = RepairShop.objects.create(
            owner=self.other_mechanic,
            name="Atelier non destinataire",
            business_type=RepairShop.BusinessType.MECHANIC,
            city="Parakou",
            district="Zongo",
            phone="+22961000001",
        )
        other_shop.vehicle_types.add(self.moto, self.car)
        self.client.force_authenticate(self.customer)
        auto_vehicle = self.client.post(
            "/api/vehicles/",
            {
                "vehicle_type": self.car.id,
                "make": "Toyota",
                "model": "Corolla",
                "year": 2018,
            },
            format="json",
        )
        moto_vehicle = self.client.post(
            "/api/vehicles/",
            {
                "vehicle_type": self.moto.id,
                "make": "Honda",
                "model": "CG 125",
            },
            format="json",
        )
        self.assertEqual(auto_vehicle.status_code, 201, auto_vehicle.data)
        self.assertEqual(moto_vehicle.status_code, 201, moto_vehicle.data)

        auto_quote = self.client.post(
            "/api/quotes/",
            {
                "shop": self.shop.id,
                "vehicle": auto_vehicle.data["id"],
                "vehicle_type": self.car.id,
                "vehicle_model": "Toyota Corolla",
                "problem": "La batterie ne charge plus.",
                "urgency": "planned",
                "category": "battery",
                "location": "Banikanni",
                "availability": "Après 15 h",
            },
            format="json",
        )
        moto_quote = self.client.post(
            "/api/quotes/",
            {
                "shop": self.shop.id,
                "vehicle": moto_vehicle.data["id"],
                "vehicle_type": self.moto.id,
                "vehicle_model": "Honda CG 125",
                "problem": "Le moteur cale.",
                "urgency": "immediate",
                "category": "engine",
                "location": "Banikanni",
                "availability": "Après 15 h",
            },
            format="json",
        )
        self.assertEqual(auto_quote.status_code, 201, auto_quote.data)
        self.assertEqual(moto_quote.status_code, 201, moto_quote.data)
        self.assertEqual(auto_quote.data["vehicle_details"]["vehicle_type_name"], "Voiture")
        self.assertEqual(moto_quote.data["vehicle_details"]["vehicle_type_name"], "Moto")

        self.client.force_authenticate(self.mechanic)
        inbox = self.client.get("/api/quotes/")
        self.assertEqual(
            {item["id"] for item in inbox.data["results"]},
            {auto_quote.data["id"], moto_quote.data["id"]},
        )
        self.client.force_authenticate(self.other_mechanic)
        other_inbox = self.client.get("/api/quotes/")
        self.assertEqual(other_inbox.data["count"], 0)
        self.assertEqual(
            self.client.get(f"/api/quotes/{auto_quote.data['id']}/").status_code,
            404,
        )
        self.assertEqual(
            self.client.get(f"/api/vehicles/{auto_vehicle.data['id']}/").status_code,
            404,
        )

    def test_request_photos_are_uploaded_and_only_participants_can_download_them(self):
        image_buffer = BytesIO()
        Image.new("RGB", (2, 2), color="blue").save(image_buffer, format="PNG")
        image = SimpleUploadedFile(
            "problem.png", image_buffer.getvalue(), content_type="image/png"
        )
        with tempfile.TemporaryDirectory() as media_root:
            with self.settings(MEDIA_ROOT=media_root):
                self.client.force_authenticate(self.customer)
                created = self.client.post(
                    "/api/quotes/",
                    {
                        "shop": self.shop.id,
                        "vehicle_type": self.moto.id,
                        "vehicle_model": "Honda CG 125",
                        "problem": "Le phare ne s'allume plus.",
                        "urgency": "planned",
                        "category": "electrical",
                        "location": "Banikanni",
                        "availability": "Après 15 h",
                        "images[0]": image,
                    },
                    format="multipart",
                )
                self.assertEqual(created.status_code, 201, created.data)
                attachment = created.data["attachments"][0]
                self.assertTrue(attachment["image"].startswith("/quotes/"))
                path = f"/api{attachment['image']}"
                uploaded_attachment = QuoteAttachment.objects.get(
                    pk=attachment["id"]
                )
                self.addCleanup(uploaded_attachment.image.delete, False)

                self.client.force_authenticate(self.other_mechanic)
                self.assertEqual(self.client.get(path).status_code, 404)
                self.client.force_authenticate(self.mechanic)
                downloaded = self.client.get(path)
                self.assertEqual(downloaded.status_code, 200)
                self.assertEqual(downloaded["Content-Type"], "image/png")
                self.assertEqual(downloaded["Cache-Control"], "private, no-store")
                self.assertEqual(
                    self.client.get(
                        f"/media/{uploaded_attachment.image.name}"
                    ).status_code,
                    404,
                )

    def test_mechanic_acceptance_refusal_questions_and_notifications(self):
        accepted_quote = self.create_quote_via_api()
        declined_quote = self.create_quote_via_api()
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.mechanic,
                quote=accepted_quote,
                event="request_created",
            ).exists()
        )

        self.client.force_authenticate(self.mechanic)
        accepted = self.client.post(
            f"/api/quotes/{accepted_quote.id}/accept-request/", {}, format="json"
        )
        declined = self.client.post(
            f"/api/quotes/{declined_quote.id}/decline-request/",
            {"reason": "Atelier complet cette semaine."},
            format="json",
        )
        self.assertEqual(accepted.status_code, 200, accepted.data)
        self.assertEqual(accepted.data["status"], QuoteRequest.Status.DISCUSSION)
        self.assertEqual(declined.status_code, 200, declined.data)
        self.assertEqual(declined.data["status"], QuoteRequest.Status.DECLINED)

        question = self.client.post(
            f"/api/quotes/{accepted_quote.id}/message/",
            {"message": "Depuis quand le moteur cale-t-il ?"},
            format="json",
        )
        self.assertEqual(question.status_code, 200, question.data)
        self.assertEqual(question.data["messages"][0]["message"], "Depuis quand le moteur cale-t-il ?")

        self.client.force_authenticate(self.customer)
        declined_detail = self.client.get(f"/api/quotes/{declined_quote.id}/")
        self.assertEqual(
            declined_detail.data["refusal_reason"],
            "Atelier complet cette semaine.",
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.customer,
                quote=declined_quote,
                event="request_declined",
            ).exists()
        )
        client_notifications = self.client.get("/api/notifications/")
        self.assertEqual(client_notifications.status_code, 200)
        notification = Notification.objects.filter(
            recipient=self.customer, quote=declined_quote
        ).first()
        marked = self.client.post(
            f"/api/notifications/{notification.id}/read/", {}, format="json"
        )
        self.assertEqual(marked.status_code, 200)
        self.assertTrue(marked.data["is_read"])

    def test_detailed_quote_total_acceptance_refusal_and_revision_history(self):
        quote = self.create_quote_via_api()
        self.client.force_authenticate(self.mechanic)
        accepted_request = self.client.post(
            f"/api/quotes/{quote.id}/accept-request/", {}, format="json"
        )
        self.assertEqual(accepted_request.status_code, 200)

        first_offer_response = self.create_offer(quote)
        first_offer = first_offer_response.data
        self.assertEqual(first_offer["version"], 1)
        self.assertEqual(first_offer["currency"], "XOF")
        self.assertEqual(first_offer["total"], "14000")
        self.assertEqual(first_offer["status"], QuoteOffer.Status.SENT)

        self.client.force_authenticate(self.customer)
        request_changes = self.client.post(
            f"/api/quotes/{quote.id}/request-changes/",
            {"reason": "Pouvez-vous détailler le prix du filtre ?"},
            format="json",
        )
        self.assertEqual(request_changes.status_code, 200, request_changes.data)
        self.assertEqual(request_changes.data["status"], QuoteRequest.Status.DISCUSSION)

        second_offer_response = self.create_offer(
            quote,
            labor_cost="6000",
            parts=[{"name": "Filtre renforcé", "quantity": 1, "unit_price": "5000"}],
        )
        second_offer = second_offer_response.data
        self.assertEqual(second_offer["version"], 2)
        self.assertEqual(second_offer["total"], "12000")
        quote.refresh_from_db()
        self.assertEqual(
            quote.offers.get(version=1).status,
            QuoteOffer.Status.SUPERSEDED,
        )

        self.client.force_authenticate(self.customer)
        decision = self.client.post(
            f"/api/quotes/{quote.id}/decide/",
            {"decision": "accepted"},
            format="json",
        )
        self.assertEqual(decision.status_code, 200, decision.data)
        self.assertEqual(decision.data["status"], QuoteRequest.Status.QUOTE_ACCEPTED)
        self.assertEqual(
            quote.offers.get(version=2).status,
            QuoteOffer.Status.ACCEPTED,
        )
        quote.refresh_from_db()
        self.assertEqual(
            quote.offers.get(version=2).status,
            QuoteOffer.Status.ACCEPTED,
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.mechanic,
                quote=quote,
                event="quote_accepted",
            ).exists()
        )

        refused_quote = self.create_quote_via_api()
        self.client.force_authenticate(self.mechanic)
        self.client.post(
            f"/api/quotes/{refused_quote.id}/accept-request/", {}, format="json"
        )
        self.create_offer(refused_quote)
        self.client.force_authenticate(self.customer)
        refused = self.client.post(
            f"/api/quotes/{refused_quote.id}/decide/",
            {"decision": "declined"},
            format="json",
        )
        self.assertEqual(refused.status_code, 200, refused.data)
        self.assertEqual(refused.data["status"], QuoteRequest.Status.QUOTE_DECLINED)

    def test_expired_estimate_cannot_be_accepted(self):
        quote = self.create_quote_via_api()
        self.client.force_authenticate(self.mechanic)
        self.client.post(
            f"/api/quotes/{quote.id}/accept-request/", {}, format="json"
        )
        self.create_offer(quote)
        QuoteOffer.objects.filter(quote=quote).update(
            valid_until=timezone.localdate() - timedelta(days=1)
        )

        self.client.force_authenticate(self.customer)
        detail = self.client.get(f"/api/quotes/{quote.id}/")
        self.assertTrue(detail.data["offers"][0]["is_expired"])
        accepted = self.client.post(
            f"/api/quotes/{quote.id}/decide/",
            {"decision": "accepted"},
            format="json",
        )
        self.assertEqual(accepted.status_code, 400)
        quote.refresh_from_db()
        self.assertEqual(quote.status, QuoteRequest.Status.QUOTE_SENT)

    def test_appointment_proposal_confirmation_conflict_cancellation_and_permissions(self):
        quote = self.create_quote_via_api()
        self.client.force_authenticate(self.mechanic)
        self.client.post(
            f"/api/quotes/{quote.id}/accept-request/", {}, format="json"
        )
        self.create_offer(quote)
        self.client.force_authenticate(self.customer)
        self.client.post(
            f"/api/quotes/{quote.id}/decide/",
            {"decision": "accepted"},
            format="json",
        )

        scheduled_at = timezone.now() + timedelta(days=3)
        self.client.force_authenticate(self.mechanic)
        proposal = self.client.post(
            f"/api/quotes/{quote.id}/appointments/",
            {"scheduled_at": scheduled_at.isoformat(), "note": "Au garage."},
            format="json",
        )
        self.assertEqual(proposal.status_code, 201, proposal.data)
        appointment_id = proposal.data["id"]

        self.client.force_authenticate(self.other_mechanic)
        self.assertEqual(
            self.client.post(
                f"/api/appointments/{appointment_id}/confirm/", {}, format="json"
            ).status_code,
            404,
        )
        self.client.force_authenticate(self.customer)
        confirmed = self.client.post(
            f"/api/appointments/{appointment_id}/confirm/", {}, format="json"
        )
        self.assertEqual(confirmed.status_code, 200, confirmed.data)
        self.assertEqual(confirmed.data["status"], Appointment.Status.CONFIRMED)
        quote.refresh_from_db()
        self.assertEqual(quote.status, QuoteRequest.Status.APPOINTMENT_CONFIRMED)

        second_quote = self.create_quote_via_api()
        self.client.force_authenticate(self.mechanic)
        self.client.post(
            f"/api/quotes/{second_quote.id}/accept-request/", {}, format="json"
        )
        self.create_offer(second_quote)
        self.client.force_authenticate(self.customer)
        self.client.post(
            f"/api/quotes/{second_quote.id}/decide/",
            {"decision": "accepted"},
            format="json",
        )
        self.client.force_authenticate(self.mechanic)
        conflicting = self.client.post(
            f"/api/quotes/{second_quote.id}/appointments/",
            {"scheduled_at": scheduled_at.isoformat()},
            format="json",
        )
        self.assertEqual(conflicting.status_code, 400)

        self.client.force_authenticate(self.customer)
        cancelled = self.client.post(
            f"/api/appointments/{appointment_id}/cancel/", {}, format="json"
        )
        self.assertEqual(cancelled.status_code, 200, cancelled.data)
        quote.refresh_from_db()
        self.assertEqual(quote.status, QuoteRequest.Status.QUOTE_ACCEPTED)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.mechanic,
                quote=quote,
                event="appointment_cancelled",
            ).exists()
        )

        self.client.force_authenticate(self.mechanic)
        self.assertEqual(self.client.get("/api/appointments/").status_code, 200)
        replacement = self.client.post(
            f"/api/quotes/{quote.id}/appointments/",
            {
                "scheduled_at": (timezone.now() + timedelta(days=5)).isoformat(),
                "note": "Nouveau créneau.",
            },
            format="json",
        )
        self.assertEqual(replacement.status_code, 201, replacement.data)
        self.client.force_authenticate(self.customer)
        replacement_confirmed = self.client.post(
            f"/api/appointments/{replacement.data['id']}/confirm/",
            {},
            format="json",
        )
        self.assertEqual(replacement_confirmed.status_code, 200)
        self.client.force_authenticate(self.mechanic)
        started = self.client.post(
            f"/api/quotes/{quote.id}/start/", {}, format="json"
        )
        self.assertEqual(started.status_code, 200, started.data)
        self.assertEqual(started.data["status"], QuoteRequest.Status.IN_PROGRESS)

        additional_offer = self.create_offer(
            quote,
            labor_cost="2500",
            parts=[{"name": "Courroie", "quantity": 1, "unit_price": "3000"}],
        )
        self.assertTrue(additional_offer.data["is_supplemental"])
        self.assertEqual(
            additional_offer.data["resume_status"],
            QuoteRequest.Status.IN_PROGRESS,
        )
        quote.refresh_from_db()
        self.assertEqual(quote.status, QuoteRequest.Status.QUOTE_SENT)
        self.client.force_authenticate(self.mechanic)
        blocked_start = self.client.post(
            f"/api/quotes/{quote.id}/start/", {}, format="json"
        )
        self.assertEqual(blocked_start.status_code, 400)

        self.client.force_authenticate(self.customer)
        declined_additional = self.client.post(
            f"/api/quotes/{quote.id}/decide/",
            {"decision": "declined"},
            format="json",
        )
        self.assertEqual(
            declined_additional.data["status"],
            QuoteRequest.Status.IN_PROGRESS,
        )
        quote.refresh_from_db()
        self.assertEqual(
            quote.offers.get(version=1).status,
            QuoteOffer.Status.ACCEPTED,
        )

        revised_additional = self.create_offer(
            quote,
            labor_cost="2000",
            parts=[{"name": "Courroie", "quantity": 1, "unit_price": "2500"}],
        )
        self.assertTrue(revised_additional.data["is_supplemental"])
        self.client.force_authenticate(self.customer)
        accepted_additional = self.client.post(
            f"/api/quotes/{quote.id}/decide/",
            {"decision": "accepted"},
            format="json",
        )
        self.assertEqual(
            accepted_additional.data["status"],
            QuoteRequest.Status.IN_PROGRESS,
        )

    def test_client_and_mechanic_permissions_and_admin_reporting(self):
        quote = self.create_quote_via_api()
        other_customer = User.objects.create_user(
            username="other-client",
            email="other-client@example.com",
            password="OtherClientPass123!secure",
            role=User.Role.CUSTOMER,
        )
        self.client.force_authenticate(other_customer)
        self.assertEqual(
            self.client.get(f"/api/quotes/{quote.id}/").status_code,
            404,
        )

        self.client.force_authenticate(self.mechanic)
        forbidden_decision = self.client.post(
            f"/api/quotes/{quote.id}/decide/",
            {"decision": "accepted"},
            format="json",
        )
        self.assertEqual(forbidden_decision.status_code, 403)

        self.client.force_authenticate(self.customer)
        report = self.client.post(
            f"/api/quotes/{quote.id}/report/",
            {"reason": "Le réparateur ne répond pas."},
            format="json",
        )
        self.assertEqual(report.status_code, 201, report.data)
        self.assertEqual(self.client.get("/api/reports/").data["count"], 1)

        admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="AdminPass123!secure",
        )
        self.client.force_authenticate(admin)
        reports = self.client.get("/api/reports/")
        self.assertEqual(reports.status_code, 200)
        self.assertEqual(reports.data["count"], 1)
        resolved = self.client.post(
            f"/api/reports/{report.data['id']}/resolve/", {}, format="json"
        )
        self.assertEqual(resolved.status_code, 200, resolved.data)
        self.assertEqual(resolved.data["status"], "resolved")
