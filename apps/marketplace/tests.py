from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import QuoteRequest, RepairShop, Service, VehicleType


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
        self.assertFalse(self.shop.reviews.get(customer=self.customer).is_approved)

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
