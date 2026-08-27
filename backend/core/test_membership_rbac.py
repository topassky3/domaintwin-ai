from __future__ import annotations

import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings

from .actor_audit import actor_snapshot
from .models import ManagedDomain, Membership, Organization
from .rbac import ADMIN, ROLE_GROUPS, VIEWER


@override_settings(DOMAIN_TWIN_TESTING=False)
class MembershipAuthorizationCutoverTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="multi-role", password="pw")
        self.superuser = User.objects.create_superuser(
            username="tenant-root",
            password="pw",
            email="root@example.com",
        )
        self.unscoped_superuser = User.objects.create_superuser(
            username="unscoped-root",
            password="pw",
            email="unscoped@example.com",
        )

        admin_group = Group.objects.create(name=ROLE_GROUPS[ADMIN])
        self.user.groups.add(admin_group)

        self.org_a = Organization.objects.create(name="Alpha Tenant", slug="alpha-tenant")
        self.org_b = Organization.objects.create(name="Beta Tenant", slug="beta-tenant")
        self.membership_a = Membership.objects.create(
            organization=self.org_a,
            user=self.user,
            role=Membership.Role.VIEWER,
        )
        self.membership_b = Membership.objects.create(
            organization=self.org_b,
            user=self.user,
            role=Membership.Role.ADMIN,
        )
        self.root_membership = Membership.objects.create(
            organization=self.org_a,
            user=self.superuser,
            role=Membership.Role.VIEWER,
        )
        ManagedDomain.objects.create(organization=self.org_a, name="alpha.example")
        ManagedDomain.objects.create(organization=self.org_b, name="beta.example")

    def _select(self, organization):
        response = self.client.post(
            "/api/auth/active-organization/",
            data=json.dumps({"organizationId": str(organization.id)}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        return response

    def test_multiple_memberships_require_selection_before_private_authorization(self):
        self.client.force_login(self.user)
        response = self.client.get("/api/namecom/status/")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "tenant_selection_required")

        me = self.client.get("/api/auth/me/")
        self.assertEqual(me.status_code, 200)
        self.assertTrue(me.json()["selectionRequired"])
        self.assertIsNone(me.json()["activeOrganization"])
        self.assertIsNone(me.json()["user"]["role"])
        self.assertEqual(me.json()["user"]["capabilities"], [])

    @patch("core.monitor_views.NameComClient")
    def test_global_admin_group_does_not_elevate_viewer_membership(self, client_cls):
        self.client.force_login(self.user)
        self._select(self.org_a)
        response = self.client.post("/api/monitor/domains/alpha.example/evaluate/")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["role"], VIEWER)
        client_cls.assert_not_called()

    def test_membership_admin_authorizes_even_when_group_authority_is_irrelevant(self):
        self.client.force_login(self.user)
        self._select(self.org_b)
        response = self.client.post("/api/future-state-change/")
        self.assertEqual(response.status_code, 404)

    def test_auth_me_tracks_active_organization_and_membership_role(self):
        self.client.force_login(self.user)
        self._select(self.org_a)
        alpha = self.client.get("/api/auth/me/").json()
        self.assertEqual(alpha["user"]["role"], VIEWER)
        self.assertEqual(alpha["activeOrganization"]["organizationId"], str(self.org_a.id))

        self._select(self.org_b)
        beta = self.client.get("/api/auth/me/").json()
        self.assertEqual(beta["user"]["role"], ADMIN)
        self.assertEqual(beta["activeOrganization"]["organizationId"], str(self.org_b.id))

    def test_superuser_is_not_cross_tenant_admin_bypass(self):
        self.client.force_login(self.superuser)
        response = self.client.post("/api/future-state-change/")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["role"], VIEWER)

        self.client.force_login(self.unscoped_superuser)
        unscoped = self.client.get("/api/namecom/status/")
        self.assertEqual(unscoped.status_code, 403)
        self.assertEqual(unscoped.json()["error"]["code"], "no_active_membership")

    def test_actor_audit_role_is_membership_derived(self):
        self.assertEqual(actor_snapshot(self.user, membership=self.membership_a)["role"], VIEWER)
        self.assertEqual(actor_snapshot(self.user, membership=self.membership_b)["role"], ADMIN)

    def test_revoked_selected_membership_is_not_authority(self):
        self.client.force_login(self.user)
        self._select(self.org_a)
        self.membership_a.is_active = False
        self.membership_a.save(update_fields=["is_active", "updated_at"])

        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["activeOrganization"]["organizationId"], str(self.org_b.id))
        self.assertEqual(response.json()["user"]["role"], ADMIN)
