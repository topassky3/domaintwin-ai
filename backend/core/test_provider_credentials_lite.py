from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from .models import Membership, Organization, ProviderConnection
from .provider_middleware import requires_namecom_provider
from .tenant import ACTIVE_ORGANIZATION_SESSION_KEY


@override_settings(
    DOMAIN_TWIN_TESTING=False,
    NAMECOM_ENVIRONMENT="sandbox",
    NAMECOM_USERNAME="p4-demo-user",
    NAMECOM_API_TOKEN="P4_SERVER_ONLY_TOKEN_DO_NOT_LEAK",
)
class ProviderCredentialsLiteSecurityTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="p4-admin", password="pw")
        self.org_a = Organization.objects.create(name="P4 Tenant A", slug="p4-a")
        self.org_b = Organization.objects.create(name="P4 Tenant B", slug="p4-b")
        self.membership_a = Membership.objects.create(
            organization=self.org_a,
            user=self.user,
            role=Membership.Role.ADMIN,
        )
        self.membership_b = Membership.objects.create(
            organization=self.org_b,
            user=self.user,
            role=Membership.Role.ADMIN,
        )
        self.client.force_login(self.user)
        self._select_in_session(self.org_a)

    def _select_in_session(self, organization):
        session = self.client.session
        session[ACTIVE_ORGANIZATION_SESSION_KEY] = str(organization.id)
        session.save()

    def _provider_stub(self, client_factory):
        provider = client_factory.return_value
        provider.environment = "sandbox"
        provider.base_url = "https://api.dev.name.com"
        provider.username = "p4-demo-user-test"
        provider.hello.return_value = {
            "username": "p4-demo-user-test",
            "serverTime": "2026-08-28T20:00:00Z",
        }
        return provider

    def test_provider_connection_contains_no_secret_material(self):
        field_names = {field.name.lower() for field in ProviderConnection._meta.fields}
        for forbidden in ("token", "secret", "password", "username", "credential", "api_key"):
            self.assertFalse(any(forbidden in field_name for field_name in field_names))
        self.assertEqual(
            ProviderConnection.objects.get(
                organization=self.org_a,
                provider=ProviderConnection.Provider.NAMECOM,
            ).provider,
            "name.com",
        )

    def test_missing_or_disabled_binding_fails_before_provider_code(self):
        connection = ProviderConnection.objects.get(
            organization=self.org_a,
            provider=ProviderConnection.Provider.NAMECOM,
        )
        connection.delete()

        with patch("core.views._client") as client_factory:
            missing = self.client.get("/api/namecom/status/")
        self.assertEqual(missing.status_code, 409)
        self.assertEqual(missing.json()["error"]["code"], "provider_connection_required")
        client_factory.assert_not_called()

        connection = ProviderConnection.objects.create(
            organization=self.org_a,
            provider=ProviderConnection.Provider.NAMECOM,
            is_active=False,
        )
        with patch("core.views._client") as client_factory:
            disabled = self.client.get("/api/namecom/status/")
        self.assertEqual(disabled.status_code, 409)
        client_factory.assert_not_called()
        connection.delete()

    def test_active_binding_allows_provider_but_never_returns_api_token(self):
        with patch("core.views._client") as client_factory:
            self._provider_stub(client_factory)
            response = self.client.get("/api/namecom/status/")

        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8")
        self.assertNotIn("P4_SERVER_ONLY_TOKEN_DO_NOT_LEAK", body)
        self.assertNotIn("NAMECOM_API_TOKEN", body)
        self.assertEqual(response.json()["provider"], "name.com")
        client_factory.assert_called_once()

    def test_provider_binding_follows_active_tenant_without_cross_tenant_fallback(self):
        ProviderConnection.objects.filter(
            organization=self.org_b,
            provider=ProviderConnection.Provider.NAMECOM,
        ).delete()

        with patch("core.views._client") as client_factory:
            self._provider_stub(client_factory)
            allowed = self.client.get("/api/namecom/status/")
        self.assertEqual(allowed.status_code, 200)
        client_factory.assert_called_once()

        self._select_in_session(self.org_b)
        with patch("core.views._client") as client_factory:
            denied = self.client.get("/api/namecom/status/")
        self.assertEqual(denied.status_code, 409)
        self.assertEqual(denied.json()["error"]["code"], "provider_connection_required")
        client_factory.assert_not_called()

    def test_only_real_provider_crossing_routes_are_gated(self):
        gated = [
            ("/api/namecom/status/", "GET"),
            ("/api/namecom/domains/example.com/records/", "GET"),
            ("/api/twin/domains/example.com/snapshots/", "POST"),
            ("/api/twin/domains/example.com/diff/", "GET"),
            ("/api/risk/domains/example.com/", "GET"),
            ("/api/monitor/domains/example.com/evaluate/", "POST"),
            ("/api/recovery/domains/example.com/plans/", "POST"),
            ("/api/recovery/plans/1/apply/", "POST"),
            ("/api/emergency/status/", "GET"),
            ("/api/emergency/search/", "POST"),
            ("/api/emergency/check/", "POST"),
            ("/api/emergency/domains/example.com/plans/", "POST"),
            ("/api/emergency/plans/1/apply/", "POST"),
        ]
        for path, method in gated:
            with self.subTest(path=path, method=method):
                self.assertTrue(requires_namecom_provider(path, method))

        not_gated = [
            ("/api/health/", "GET"),
            ("/api/twin/domains/example.com/snapshots/", "GET"),
            ("/api/monitor/domains/example.com/status/", "GET"),
            ("/api/recovery/domains/example.com/plans/", "GET"),
            ("/api/emergency/plans/1/approve/", "POST"),
            ("/api/namecom/status/", "OPTIONS"),
        ]
        for path, method in not_gated:
            with self.subTest(path=path, method=method):
                self.assertFalse(requires_namecom_provider(path, method))
