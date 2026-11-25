from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase


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
