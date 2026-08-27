from __future__ import annotations

import json
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase, override_settings

from .rbac import (
    ADMIN,
    APPROVER,
    BASELINE_APPROVE,
    DNS_MUTATE,
    EMERGENCY_APPLY,
    OPERATOR,
    READ,
    RECOVERY_APPLY,
    RECOVERY_APPROVE,
    RECOVERY_PREVIEW,
    ROLE_GROUPS,
    UNCLASSIFIED_MUTATION,
    VIEWER,
    authorization_for_user,
    required_capability,
    role_for_user,
)


@override_settings(DOMAIN_TWIN_TESTING=False)
class RoleAuthorizationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.viewer = User.objects.create_user(username="viewer", password="pw")
        self.operator = User.objects.create_user(username="operator", password="pw")
        self.approver = User.objects.create_user(username="approver", password="pw")
        self.admin = User.objects.create_user(username="admin", password="pw")
        self.superuser = User.objects.create_superuser(username="root", password="pw", email="root@example.com")

        for user, role in (
            (self.operator, OPERATOR),
            (self.approver, APPROVER),
            (self.admin, ADMIN),
        ):
            group = Group.objects.create(name=ROLE_GROUPS[role])
            user.groups.add(group)

    def test_authenticated_user_without_group_defaults_to_viewer(self):
        self.assertEqual(role_for_user(self.viewer), VIEWER)
        auth = authorization_for_user(self.viewer)
        self.assertEqual(auth["role"], VIEWER)
        self.assertEqual(auth["capabilities"], [READ])

    def test_superuser_is_always_admin(self):
        self.assertEqual(role_for_user(self.superuser), ADMIN)
        self.assertIn(DNS_MUTATE, authorization_for_user(self.superuser)["capabilities"])

    def test_highest_matching_role_wins(self):
        self.operator.groups.add(Group.objects.get(name=ROLE_GROUPS[APPROVER]))
        self.assertEqual(role_for_user(self.operator), APPROVER)

    def test_auth_me_exposes_role_and_capabilities(self):
        self.client.force_login(self.approver)
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 200)
        user = response.json()["user"]
        self.assertEqual(user["role"], APPROVER)
        self.assertIn(RECOVERY_APPROVE, user["capabilities"])
        self.assertNotIn(RECOVERY_APPLY, user["capabilities"])

    def test_viewer_can_read_private_operational_state(self):
        self.client.force_login(self.viewer)
        response = self.client.get("/api/monitor/domains/example.com/status/")
        self.assertEqual(response.status_code, 200)

    @patch("core.monitor_views.NameComClient")
    def test_viewer_cannot_evaluate_and_provider_is_not_called(self, client_cls):
        self.client.force_login(self.viewer)
        response = self.client.post("/api/monitor/domains/example.com/evaluate/")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["role"], VIEWER)
        self.assertEqual(response.json()["error"]["requiredCapability"], "evaluate")
        client_cls.assert_not_called()

    def test_operator_can_reach_evaluation_view(self):
        self.client.force_login(self.operator)
        response = self.client.post("/api/monitor/domains/missing.example/evaluate/")
        self.assertEqual(response.status_code, 404)

    def test_operator_can_prepare_but_cannot_approve_recovery(self):
        self.client.force_login(self.operator)
        denied = self.client.post(
            "/api/recovery/plans/999/approve/",
            data=json.dumps({"approve": True}),
            content_type="application/json",
        )
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.json()["error"]["requiredCapability"], RECOVERY_APPROVE)
        self.assertIn(RECOVERY_PREVIEW, authorization_for_user(self.operator)["capabilities"])

    def test_approver_can_reach_approval_but_cannot_apply(self):
        self.client.force_login(self.approver)
        approval = self.client.post(
            "/api/recovery/plans/999/approve/",
            data=json.dumps({"approve": True}),
            content_type="application/json",
        )
        self.assertEqual(approval.status_code, 404)

        apply_response = self.client.post("/api/recovery/plans/999/apply/")
        self.assertEqual(apply_response.status_code, 403)
        self.assertEqual(apply_response.json()["error"]["requiredCapability"], RECOVERY_APPLY)

    def test_admin_can_reach_apply_view(self):
        self.client.force_login(self.admin)
        response = self.client.post("/api/recovery/plans/999/apply/")
        self.assertEqual(response.status_code, 404)

    @patch("core.views._client")
    def test_direct_dns_mutation_is_admin_only_and_denied_before_provider(self, client_factory):
        self.client.force_login(self.operator)
        response = self.client.post(
            "/api/namecom/domains/example.com/records/",
            data=json.dumps({"type": "A", "host": "www", "answer": "203.0.113.10"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["requiredCapability"], DNS_MUTATE)
        client_factory.assert_not_called()

    def test_unknown_mutation_is_fail_closed_to_admin(self):
        self.client.force_login(self.viewer)
        denied = self.client.post("/api/future-state-change/")
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.json()["error"]["requiredCapability"], UNCLASSIFIED_MUTATION)

        self.client.force_login(self.admin)
        allowed_to_router = self.client.post("/api/future-state-change/")
        self.assertEqual(allowed_to_router.status_code, 404)

    def test_sensitive_endpoint_classifier_is_explicit(self):
        self.assertEqual(required_capability("/api/recovery/domains/a.example/plans/", "POST"), RECOVERY_PREVIEW)
        self.assertEqual(required_capability("/api/recovery/plans/7/approve/", "POST"), RECOVERY_APPROVE)
        self.assertEqual(required_capability("/api/recovery/plans/7/apply/", "POST"), RECOVERY_APPLY)
        self.assertEqual(required_capability("/api/emergency/plans/8/apply/", "POST"), EMERGENCY_APPLY)
        self.assertEqual(required_capability("/api/twin/domains/a.example/snapshots/2/known-good/", "POST"), BASELINE_APPROVE)
        self.assertEqual(required_capability("/api/namecom/domains/a.example/records/9/", "DELETE"), DNS_MUTATE)
        self.assertEqual(required_capability("/api/incidents/1/", "GET"), READ)

    def test_role_assignment_command_replaces_prior_domaintwin_role(self):
        self.viewer.groups.add(Group.objects.get(name=ROLE_GROUPS[OPERATOR]))
        out = StringIO()
        call_command("set_domaintwin_role", "viewer", ADMIN, stdout=out)
        self.viewer.refresh_from_db()
        self.assertEqual(role_for_user(self.viewer), ADMIN)
        names = set(self.viewer.groups.values_list("name", flat=True))
        self.assertIn(ROLE_GROUPS[ADMIN], names)
        self.assertNotIn(ROLE_GROUPS[OPERATOR], names)
        self.assertIn("Assigned DomainTwin role ADMIN", out.getvalue())
