from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from unittest.mock import patch


@override_settings(DOMAIN_TWIN_TESTING=False)
class PrivateWorkspaceSessionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="operator",
            email="operator@example.com",
            password="correct-horse-battery-staple",
        )

    def test_health_remains_public(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_auth_bootstrap_remains_public(self):
        response = self.client.get("/api/auth/csrf/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["csrfToken"])

    @patch("core.views._client")
    def test_anonymous_private_provider_endpoint_is_blocked_before_view(self, client_factory):
        response = self.client.get("/api/namecom/status/")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["status"], 401)
        client_factory.assert_not_called()

    def test_anonymous_private_mutation_endpoint_is_blocked(self):
        response = self.client.post("/api/recovery/domains/example.com/plans/")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["message"], "Authentication required.")

    def test_authenticated_session_reaches_private_query_endpoint(self):
        self.client.force_login(self.user)
        response = self.client.get("/api/incidents/domains/example.com/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["totalCount"], 0)
