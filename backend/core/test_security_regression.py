from __future__ import annotations

import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase, override_settings

from .models import ManagedDomain, Membership, Organization
from .rbac import ADMIN, APPROVER, OPERATOR, ROLE_GROUPS


@override_settings(DOMAIN_TWIN_TESTING=False)
class EndToEndSecurityRegressionTests(TestCase):
    """Exercise production authentication + RBAC + CSRF + tenant boundary together."""

    def setUp(self):
        User = get_user_model()
        self.viewer = User.objects.create_user(username="viewer-e2e", password="pw")
        self.operator = User.objects.create_user(username="operator-e2e", password="pw")
        self.approver = User.objects.create_user(username="approver-e2e", password="pw")
        self.admin = User.objects.create_user(username="admin-e2e", password="pw")

        groups = {
            role: Group.objects.create(name=ROLE_GROUPS[role])
            for role in (OPERATOR, APPROVER, ADMIN)
        }
        self.operator.groups.add(groups[OPERATOR])
        self.approver.groups.add(groups[APPROVER])
        self.admin.groups.add(groups[ADMIN])

        self.organization = Organization.objects.create(
            name="Security regression tenant",
            slug="security-regression",
        )
        for user, role in (
            (self.viewer, Membership.Role.VIEWER),
            (self.operator, Membership.Role.OPERATOR),
            (self.approver, Membership.Role.APPROVER),
            (self.admin, Membership.Role.ADMIN),
        ):
            Membership.objects.create(
                organization=self.organization,
                user=user,
                role=role,
            )
        for domain_name in ("example.com", "missing.example"):
            ManagedDomain.objects.create(
                organization=self.organization,
                name=domain_name,
            )

    def _client_for(self, user) -> Client:
        client = Client(enforce_csrf_checks=True)
        client.force_login(user)
        return client

    def _csrf(self, client: Client) -> str:
        response = client.get("/api/auth/csrf/")
        self.assertEqual(response.status_code, 200)
        token = response.json()["csrfToken"]
        self.assertTrue(token)
        return token

    def test_anonymous_private_read_is_401(self):
        client = Client(enforce_csrf_checks=True)
        response = client.get("/api/monitor/domains/example.com/status/")
        self.assertEqual(response.status_code, 401)

    @patch("core.monitor_views.NameComClient")
    def test_authorized_operator_mutation_without_csrf_is_403_before_view(self, client_cls):
        client = self._client_for(self.operator)
        response = client.post("/api/monitor/domains/example.com/evaluate/")
        self.assertEqual(response.status_code, 403)
        client_cls.assert_not_called()

    @patch("core.views._client")
    def test_admin_dns_mutation_without_csrf_is_403_before_provider(self, client_factory):
        client = self._client_for(self.admin)
        response = client.post(
            "/api/namecom/domains/example.com/records/",
            data=json.dumps({"type": "A", "host": "www", "answer": "203.0.113.7"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        client_factory.assert_not_called()

    def test_valid_csrf_reaches_authorized_operator_view(self):
        client = self._client_for(self.operator)
        token = self._csrf(client)
        response = client.post(
            "/api/monitor/domains/missing.example/evaluate/",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 404)

    def test_valid_csrf_does_not_bypass_rbac(self):
        client = self._client_for(self.viewer)
        token = self._csrf(client)
        response = client.post(
            "/api/monitor/domains/example.com/evaluate/",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["role"], "VIEWER")
        self.assertEqual(response.json()["error"]["requiredCapability"], "evaluate")

    @patch("core.views._client")
    def test_valid_csrf_and_admin_role_reach_dns_provider(self, client_factory):
        provider = client_factory.return_value
        provider.environment = "sandbox"
        provider.create_record.return_value = {
            "id": 9,
            "type": "A",
            "host": "www",
            "answer": "203.0.113.7",
            "ttl": 300,
        }

        client = self._client_for(self.admin)
        token = self._csrf(client)
        response = client.post(
            "/api/namecom/domains/example.com/records/",
            data=json.dumps({"type": "A", "host": "www", "answer": "203.0.113.7"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 201)
        provider.create_record.assert_called_once()

    def test_logout_invalidates_private_workspace_session(self):
        client = self._client_for(self.operator)
        token = self._csrf(client)
        logout = client.post(
            "/api/auth/logout/",
            data="{}",
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(logout.status_code, 200)

        private = client.get("/api/monitor/domains/example.com/status/")
        self.assertEqual(private.status_code, 401)

    def test_anonymous_options_remains_protocol_safe(self):
        client = Client(enforce_csrf_checks=True)
        response = client.options("/api/recovery/plans/999/apply/")
        self.assertNotEqual(response.status_code, 401)
        self.assertNotEqual(response.status_code, 403)
