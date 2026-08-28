from __future__ import annotations

import json
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from .models import ManagedDomain, Membership, Organization
from .rbac import OPERATOR, ROLE_GROUPS
from .tenant import ACTIVE_ORGANIZATION_SESSION_KEY


@override_settings(DOMAIN_TWIN_TESTING=False)
class TenantDomainBoundaryTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="tenant-user", password="pw")
        self.other = User.objects.create_user(username="no-tenant", password="pw")

        self.org_a = Organization.objects.create(name="Tenant A", slug="tenant-a")
        self.org_b = Organization.objects.create(name="Tenant B", slug="tenant-b")
        self.membership_a = Membership.objects.create(
            organization=self.org_a,
            user=self.user,
            role=Membership.Role.OPERATOR,
        )
        self.membership_b = Membership.objects.create(
            organization=self.org_b,
            user=self.user,
            role=Membership.Role.VIEWER,
        )
        self.domain_a = ManagedDomain.objects.create(
            organization=self.org_a,
            name="A.EXAMPLE.",
        )
        self.domain_b = ManagedDomain.objects.create(
            organization=self.org_b,
            name="b.example",
        )

    def _select(self, organization):
        response = self.client.post(
            "/api/auth/active-organization/",
            data=json.dumps({"organizationId": str(organization.id)}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        return response

    def test_multiple_memberships_fail_closed_until_selected(self):
        self.client.force_login(self.user)
        with patch("core.views._client") as client_factory:
            response = self.client.get("/api/namecom/domains/a.example/")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "tenant_selection_required")
        client_factory.assert_not_called()

        context = self.client.get("/api/auth/organizations/")
        self.assertEqual(context.status_code, 200)
        self.assertTrue(context.json()["selectionRequired"])
        self.assertEqual(len(context.json()["organizations"]), 2)

    def test_selection_validates_membership_and_cross_tenant_domain_is_404_before_provider(self):
        self.client.force_login(self.user)
        self._select(self.org_a)

        with patch("core.views._client") as client_factory:
            response = self.client.get("/api/namecom/domains/b.example/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["message"], "Resource not found.")
        client_factory.assert_not_called()

        outsider_org = Organization.objects.create(name="Outsider", slug="outsider")
        denied = self.client.post(
            "/api/auth/active-organization/",
            data=json.dumps({"organizationId": str(outsider_org.id)}),
            content_type="application/json",
        )
        self.assertEqual(denied.status_code, 404)

    @patch("core.views._client")
    def test_provider_inventory_is_filtered_to_active_tenant(self, client_factory):
        self.client.force_login(self.user)
        self._select(self.org_a)
        client = client_factory.return_value
        client.environment = "sandbox"
        client.list_domains.return_value = {
            "domains": [
                {"domainName": "a.example", "expireDate": "2027-01-01"},
                {"domainName": "b.example", "expireDate": "2027-01-01"},
            ],
            "nextPage": 2,
        }

        response = self.client.get("/api/namecom/domains/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [row["domainName"] for row in response.json()["domains"]],
            ["a.example"],
        )

    @patch("core.views._client")
    def test_single_membership_is_auto_selected(self, client_factory):
        single_user = get_user_model().objects.create_user(username="single", password="pw")
        Membership.objects.create(
            organization=self.org_a,
            user=single_user,
            role=Membership.Role.VIEWER,
        )
        self.client.force_login(single_user)
        client = client_factory.return_value
        client.environment = "sandbox"
        client.get_domain.return_value = {"domainName": "a.example"}

        response = self.client.get("/api/namecom/domains/a.example/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.client.session[ACTIVE_ORGANIZATION_SESSION_KEY],
            str(self.org_a.id),
        )

    def test_revoked_selected_membership_is_cleared_and_re_resolved(self):
        self.client.force_login(self.user)
        self._select(self.org_a)
        self.membership_a.is_active = False
        self.membership_a.save(update_fields=["is_active", "updated_at"])

        with patch("core.views._client") as client_factory:
            client = client_factory.return_value
            client.environment = "sandbox"
            client.get_domain.return_value = {"domainName": "b.example"}
            response = self.client.get("/api/namecom/domains/b.example/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.client.session[ACTIVE_ORGANIZATION_SESSION_KEY],
            str(self.org_b.id),
        )

    def test_user_without_membership_fails_before_provider(self):
        self.client.force_login(self.other)
        with patch("core.views._client") as client_factory:
            response = self.client.get("/api/namecom/domains/a.example/")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "no_active_membership")
        client_factory.assert_not_called()

    def test_domain_boundary_runs_before_snapshot_provider_call(self):
        operator_group, _ = Group.objects.get_or_create(name=ROLE_GROUPS[OPERATOR])
        self.user.groups.add(operator_group)
        self.client.force_login(self.user)
        self._select(self.org_a)

        with patch("core.twin_views.NameComClient") as client_cls:
            response = self.client.post("/api/twin/domains/b.example/snapshots/")
        self.assertEqual(response.status_code, 404)
        client_cls.assert_not_called()


class ManagedDomainBootstrapTests(TestCase):
    def setUp(self):
        self.org_a = Organization.objects.create(name="Tenant A", slug="tenant-a")
        self.org_b = Organization.objects.create(name="Tenant B", slug="tenant-b")

    def test_attach_command_is_canonical_idempotent_and_reversible(self):
        out = StringIO()
        call_command(
            "attach_domaintwin_domains",
            "tenant-a",
            "--domain",
            "Example.COM.",
            stdout=out,
        )
        self.assertTrue(
            ManagedDomain.objects.filter(
                organization=self.org_a,
                name="example.com",
            ).exists()
        )

        call_command(
            "attach_domaintwin_domains",
            "tenant-a",
            "--domain",
            "example.com",
            stdout=out,
        )
        self.assertEqual(ManagedDomain.objects.filter(name="example.com").count(), 1)

        call_command(
            "attach_domaintwin_domains",
            "tenant-a",
            "--domain",
            "example.com",
            "--detach",
            stdout=out,
        )
        self.assertFalse(ManagedDomain.objects.filter(name="example.com").exists())

    def test_attach_command_rejects_cross_organization_ownership_conflict(self):
        ManagedDomain.objects.create(
            organization=self.org_a,
            name="owned.example",
        )
        with self.assertRaises(CommandError):
            call_command(
                "attach_domaintwin_domains",
                "tenant-b",
                "--domain",
                "owned.example",
            )
        self.assertEqual(
            ManagedDomain.objects.get(name="owned.example").organization,
            self.org_a,
        )
