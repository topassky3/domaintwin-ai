from __future__ import annotations

import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings

from .models import (
    DomainSnapshot,
    EmergencyDomainAuditEvent,
    EmergencyDomainPlan,
    Incident,
    IncidentEvent,
    KnownGoodSnapshot,
    ManagedDomain,
    Membership,
    Organization,
    RecoveryAuditEvent,
    RecoveryPlan,
)
from .rbac import ADMIN, DNS_MUTATE, ROLE_GROUPS, VIEWER
from .tenant import ACTIVE_ORGANIZATION_SESSION_KEY


TENANT_B_SECRET = "tenant-b-private-evidence"


@override_settings(DOMAIN_TWIN_TESTING=False)
class TenantAdversarialSecurityRegressionTests(TestCase):
    """P3-E: attack the complete auth/RBAC/tenant/evidence boundary as one system."""

    def setUp(self):
        User = get_user_model()
        self.admin_a = User.objects.create_user(username="p3e-admin-a", password="pw")
        self.dual_user = User.objects.create_user(username="p3e-dual", password="pw")

        admin_group = Group.objects.create(name=ROLE_GROUPS[ADMIN])
        self.admin_a.groups.add(admin_group)

        self.org_a = Organization.objects.create(name="P3E Tenant A", slug="p3e-a")
        self.org_b = Organization.objects.create(name="P3E Tenant B", slug="p3e-b")

        self.membership_a = Membership.objects.create(
            organization=self.org_a,
            user=self.admin_a,
            role=Membership.Role.ADMIN,
        )
        self.dual_membership_a = Membership.objects.create(
            organization=self.org_a,
            user=self.dual_user,
            role=Membership.Role.VIEWER,
        )
        self.dual_membership_b = Membership.objects.create(
            organization=self.org_b,
            user=self.dual_user,
            role=Membership.Role.ADMIN,
        )

        self.domain_a = ManagedDomain.objects.create(
            organization=self.org_a,
            name="a.example",
        )
        self.domain_b = ManagedDomain.objects.create(
            organization=self.org_b,
            name="b.example",
        )

        self.snapshot_a = DomainSnapshot.objects.create(
            domain_name="a.example",
            version=1,
            records=[
                {
                    "type": "A",
                    "host": "www",
                    "answer": "203.0.113.10",
                    "ttl": 300,
                    "priority": 0,
                }
            ],
            fingerprint="a" * 64,
        )
        self.snapshot_b = DomainSnapshot.objects.create(
            domain_name="b.example",
            version=1,
            records=[
                {
                    "type": "A",
                    "host": "private",
                    "answer": "198.51.100.99",
                    "ttl": 300,
                    "priority": 0,
                }
            ],
            fingerprint="b" * 64,
        )

        self.incident_a = Incident.objects.create(
            domain_name="a.example",
            baseline_snapshot=self.snapshot_a,
            score=80,
            severity="HIGH",
            factors=[],
            evidence={"tenant": "a"},
            evidence_fingerprint="1" * 64,
        )
        self.incident_b = Incident.objects.create(
            domain_name="b.example",
            baseline_snapshot=self.snapshot_b,
            score=95,
            severity="CRITICAL",
            factors=[],
            evidence={"secret": TENANT_B_SECRET},
            evidence_fingerprint="2" * 64,
        )
        IncidentEvent.objects.create(
            incident=self.incident_b,
            sequence=1,
            event_type="PRIVATE_EVENT",
            payload={"secret": TENANT_B_SECRET},
        )

        self.recovery_a = RecoveryPlan.objects.create(
            domain_name="a.example",
            baseline_snapshot=self.snapshot_a,
            incident=self.incident_a,
            live_fingerprint_before="3" * 64,
            target_fingerprint="a" * 64,
            plan_fingerprint="4" * 64,
            operations=[],
        )
        self.recovery_b = RecoveryPlan.objects.create(
            domain_name="b.example",
            baseline_snapshot=self.snapshot_b,
            incident=self.incident_b,
            live_fingerprint_before="5" * 64,
            target_fingerprint="b" * 64,
            plan_fingerprint="6" * 64,
            operations=[{"private": TENANT_B_SECRET}],
        )
        RecoveryAuditEvent.objects.create(
            plan=self.recovery_b,
            sequence=1,
            event_type="PRIVATE_AUDIT",
            payload={"secret": TENANT_B_SECRET},
        )

        self.emergency_a = EmergencyDomainPlan.objects.create(
            source_domain_name="a.example",
            target_domain_name="a-rescue.example",
            baseline_snapshot=self.snapshot_a,
            expected_fingerprint="a" * 64,
            plan_fingerprint="7" * 64,
            idempotency_key="p3e-a-emergency",
            operations=[],
        )
        self.emergency_b = EmergencyDomainPlan.objects.create(
            source_domain_name="b.example",
            target_domain_name="b-rescue.example",
            baseline_snapshot=self.snapshot_b,
            expected_fingerprint="b" * 64,
            plan_fingerprint="8" * 64,
            idempotency_key="p3e-b-emergency",
            operations=[{"private": TENANT_B_SECRET}],
        )
        EmergencyDomainAuditEvent.objects.create(
            plan=self.emergency_b,
            sequence=1,
            event_type="PRIVATE_AUDIT",
            payload={"secret": TENANT_B_SECRET},
        )

    def _login_a(self):
        self.client.force_login(self.admin_a)
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["activeOrganization"]["organizationId"],
            str(self.org_a.id),
        )

    def _select(self, organization):
        response = self.client.post(
            "/api/auth/active-organization/",
            data=json.dumps({"organizationId": str(organization.id)}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        return response

    def assert_non_disclosing_404(self, response):
        self.assertEqual(response.status_code, 404)
        body = response.content.decode("utf-8", errors="replace")
        self.assertNotIn(TENANT_B_SECRET, body)
        if response.headers.get("Content-Type", "").startswith("application/json"):
            self.assertEqual(response.json()["error"]["message"], "Resource not found.")

    def test_cross_tenant_domain_routes_fail_before_provider_and_mutation(self):
        self._login_a()

        with patch("core.views._client") as client_factory:
            response = self.client.get("/api/namecom/domains/b.example/")
        self.assert_non_disclosing_404(response)
        client_factory.assert_not_called()

        with patch("core.views._client") as client_factory:
            response = self.client.post(
                "/api/namecom/domains/b.example/records/",
                data=json.dumps({"type": "A", "host": "www", "answer": "203.0.113.50"}),
                content_type="application/json",
            )
        self.assert_non_disclosing_404(response)
        client_factory.assert_not_called()

        with patch("core.twin_views.NameComClient") as client_cls:
            response = self.client.post("/api/twin/domains/b.example/snapshots/")
        self.assert_non_disclosing_404(response)
        client_cls.assert_not_called()

        with patch("core.monitor_views.NameComClient") as client_cls:
            response = self.client.post("/api/monitor/domains/b.example/evaluate/")
        self.assert_non_disclosing_404(response)
        client_cls.assert_not_called()

        with patch("core.risk_views.NameComClient") as client_cls:
            response = self.client.get("/api/risk/domains/b.example/")
        self.assert_non_disclosing_404(response)
        client_cls.assert_not_called()

    @patch("core.views._client")
    def test_inventory_and_domain_lists_cannot_expose_tenant_b(self, client_factory):
        self._login_a()
        provider = client_factory.return_value
        provider.environment = "sandbox"
        provider.list_domains.return_value = {
            "domains": [
                {"domainName": "a.example"},
                {"domainName": "b.example", "renewalPrice": 999},
            ]
        }
        response = self.client.get("/api/namecom/domains/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["domainName"] for row in response.json()["domains"]], ["a.example"])

        for url in (
            "/api/incidents/domains/b.example/",
            "/api/recovery/domains/b.example/plans/",
            "/api/emergency/domains/b.example/plans/",
        ):
            with self.subTest(url=url):
                self.assert_non_disclosing_404(self.client.get(url))

    def test_manipulated_snapshot_ids_are_domain_bound_and_non_disclosing(self):
        self._login_a()

        detail = self.client.get(
            f"/api/twin/domains/a.example/snapshots/{self.snapshot_b.id}/"
        )
        self.assertEqual(detail.status_code, 404)
        self.assertNotIn(TENANT_B_SECRET, detail.content.decode("utf-8", errors="replace"))

        mark = self.client.post(
            f"/api/twin/domains/a.example/snapshots/{self.snapshot_b.id}/known-good/"
        )
        self.assertEqual(mark.status_code, 404)
        self.assertFalse(KnownGoodSnapshot.objects.filter(domain_name="a.example").exists())

        with patch("core.twin_views.NameComClient") as client_cls:
            diff = self.client.get(
                f"/api/twin/domains/a.example/diff/?snapshot_id={self.snapshot_b.id}"
            )
        self.assert_non_disclosing_404(diff)
        client_cls.assert_not_called()

    def test_cross_tenant_object_ids_and_actor_audit_are_hidden_before_execution(self):
        self._login_a()

        self.assert_non_disclosing_404(
            self.client.get(f"/api/incidents/{self.incident_b.id}/")
        )

        with patch("core.ai_views.generate_incident_explanation") as generate, patch(
            "core.ai_views.build_evidence_bundle"
        ) as build_bundle:
            ai = self.client.post(
                f"/api/ai/incidents/{self.incident_b.id}/explanation/"
            )
        self.assert_non_disclosing_404(ai)
        generate.assert_not_called()
        build_bundle.assert_not_called()

        self.assert_non_disclosing_404(
            self.client.get(f"/api/recovery/plans/{self.recovery_b.id}/")
        )
        with patch("core.recovery_views.approve_recovery_plan_as") as approve:
            approval = self.client.post(
                f"/api/recovery/plans/{self.recovery_b.id}/approve/",
                data=json.dumps({"approve": True}),
                content_type="application/json",
            )
        self.assert_non_disclosing_404(approval)
        approve.assert_not_called()
        with patch("core.recovery_views.apply_recovery_plan_as") as apply_plan:
            applied = self.client.post(f"/api/recovery/plans/{self.recovery_b.id}/apply/")
        self.assert_non_disclosing_404(applied)
        apply_plan.assert_not_called()

        self.assert_non_disclosing_404(
            self.client.get(f"/api/emergency/plans/{self.emergency_b.id}/")
        )
        with patch("core.emergency_views.approve_emergency_plan_as") as approve:
            approval = self.client.post(
                f"/api/emergency/plans/{self.emergency_b.id}/approve/",
                data=json.dumps({"approve": True}),
                content_type="application/json",
            )
        self.assert_non_disclosing_404(approval)
        approve.assert_not_called()
        with patch("core.emergency_views.NameComClient") as client_cls, patch(
            "core.emergency_views.apply_emergency_plan_as"
        ) as apply_plan:
            applied = self.client.post(
                f"/api/emergency/plans/{self.emergency_b.id}/apply/",
                data=json.dumps(
                    {"execute": True, "targetDomain": self.emergency_b.target_domain_name}
                ),
                content_type="application/json",
            )
        self.assert_non_disclosing_404(applied)
        client_cls.assert_not_called()
        apply_plan.assert_not_called()

    def test_tampered_session_and_nonmember_selection_cannot_switch_tenant(self):
        self.client.force_login(self.admin_a)
        session = self.client.session
        session[ACTIVE_ORGANIZATION_SESSION_KEY] = str(self.org_b.id)
        session.save()

        repaired = self.client.get("/api/auth/me/")
        self.assertEqual(repaired.status_code, 200)
        self.assertEqual(
            repaired.json()["activeOrganization"]["organizationId"],
            str(self.org_a.id),
        )
        self.assertEqual(repaired.json()["user"]["role"], ADMIN)
        self.assertEqual(
            self.client.session[ACTIVE_ORGANIZATION_SESSION_KEY],
            str(self.org_a.id),
        )

        denied = self.client.post(
            "/api/auth/active-organization/",
            data=json.dumps({"organizationId": str(self.org_b.id)}),
            content_type="application/json",
        )
        self.assertEqual(denied.status_code, 404)
        self.assertEqual(denied.json()["error"]["code"], "organization_not_available")

        session = self.client.session
        session[ACTIVE_ORGANIZATION_SESSION_KEY] = "not-a-uuid"
        session.save()
        repaired_again = self.client.get("/api/auth/me/")
        self.assertEqual(
            repaired_again.json()["activeOrganization"]["organizationId"],
            str(self.org_a.id),
        )

    def test_revoked_membership_and_inactive_organization_fail_before_provider(self):
        self._login_a()
        self.membership_a.is_active = False
        self.membership_a.save(update_fields=["is_active", "updated_at"])

        with patch("core.views._client") as client_factory:
            revoked = self.client.get("/api/namecom/status/")
        self.assertEqual(revoked.status_code, 403)
        self.assertEqual(revoked.json()["error"]["code"], "no_active_membership")
        client_factory.assert_not_called()

        self.membership_a.is_active = True
        self.membership_a.save(update_fields=["is_active", "updated_at"])
        self.org_a.is_active = False
        self.org_a.save(update_fields=["is_active", "updated_at"])
        with patch("core.views._client") as client_factory:
            inactive_org = self.client.get("/api/namecom/status/")
        self.assertEqual(inactive_org.status_code, 403)
        self.assertEqual(inactive_org.json()["error"]["code"], "no_active_membership")
        client_factory.assert_not_called()

    def test_membership_role_change_is_effective_without_relogin_or_group_override(self):
        self._login_a()
        self.membership_a.role = Membership.Role.VIEWER
        self.membership_a.save(update_fields=["role", "updated_at"])

        with patch("core.views._client") as client_factory:
            denied = self.client.post(
                "/api/namecom/domains/a.example/records/",
                data=json.dumps({"type": "A", "host": "www", "answer": "203.0.113.50"}),
                content_type="application/json",
            )
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.json()["error"]["role"], VIEWER)
        self.assertEqual(denied.json()["error"]["requiredCapability"], DNS_MUTATE)
        client_factory.assert_not_called()

        self.membership_a.role = Membership.Role.ADMIN
        self.membership_a.save(update_fields=["role", "updated_at"])
        allowed_to_router = self.client.post("/api/future-state-change/")
        self.assertEqual(allowed_to_router.status_code, 404)

    def test_inactive_managed_domain_revokes_domain_and_derived_resource_access(self):
        self._login_a()
        self.domain_a.is_active = False
        self.domain_a.save(update_fields=["is_active", "updated_at"])

        with patch("core.views._client") as client_factory:
            domain = self.client.get("/api/namecom/domains/a.example/")
        self.assert_non_disclosing_404(domain)
        client_factory.assert_not_called()

        self.assert_non_disclosing_404(
            self.client.get(f"/api/incidents/{self.incident_a.id}/")
        )
        with patch("core.recovery_views.apply_recovery_plan_as") as apply_plan:
            recovery = self.client.post(f"/api/recovery/plans/{self.recovery_a.id}/apply/")
        self.assert_non_disclosing_404(recovery)
        apply_plan.assert_not_called()

        with patch("core.emergency_views.NameComClient") as client_cls, patch(
            "core.emergency_views.apply_emergency_plan_as"
        ) as apply_plan:
            emergency = self.client.post(
                f"/api/emergency/plans/{self.emergency_a.id}/apply/",
                data=json.dumps(
                    {"execute": True, "targetDomain": self.emergency_a.target_domain_name}
                ),
                content_type="application/json",
            )
        self.assert_non_disclosing_404(emergency)
        client_cls.assert_not_called()
        apply_plan.assert_not_called()

    def test_switching_active_organization_switches_data_and_role_without_bleed(self):
        self.client.force_login(self.dual_user)
        self._select(self.org_a)
        alpha = self.client.get("/api/auth/me/").json()
        self.assertEqual(alpha["user"]["role"], VIEWER)
        self.assertEqual(self.client.get(f"/api/incidents/{self.incident_a.id}/").status_code, 200)
        self.assert_non_disclosing_404(
            self.client.get(f"/api/incidents/{self.incident_b.id}/")
        )
        with patch("core.monitor_views.NameComClient") as client_cls:
            denied = self.client.post("/api/monitor/domains/a.example/evaluate/")
        self.assertEqual(denied.status_code, 403)
        client_cls.assert_not_called()

        self._select(self.org_b)
        beta = self.client.get("/api/auth/me/").json()
        self.assertEqual(beta["user"]["role"], ADMIN)
        self.assertEqual(self.client.get(f"/api/incidents/{self.incident_b.id}/").status_code, 200)
        self.assert_non_disclosing_404(
            self.client.get(f"/api/incidents/{self.incident_a.id}/")
        )
        self.assertEqual(self.client.post("/api/future-state-change/").status_code, 404)

    def test_corrupted_known_good_chain_fails_before_provider_across_evidence_flows(self):
        self._login_a()
        KnownGoodSnapshot.objects.create(domain_name="a.example", snapshot=self.snapshot_b)
        self.incident_a.status = Incident.Status.RESOLVED
        self.incident_a.save(update_fields=["status", "resolved_at", "last_seen_at"])

        with patch("core.risk_views.NameComClient") as client_cls:
            risk = self.client.get("/api/risk/domains/a.example/")
        self.assertEqual(risk.status_code, 404)
        client_cls.assert_not_called()

        with patch("core.monitor_views.NameComClient") as client_cls:
            monitor = self.client.post("/api/monitor/domains/a.example/evaluate/")
        self.assert_non_disclosing_404(monitor)
        client_cls.assert_not_called()

        with patch("core.twin_views.NameComClient") as client_cls:
            diff = self.client.get("/api/twin/domains/a.example/diff/")
        self.assert_non_disclosing_404(diff)
        client_cls.assert_not_called()

        with patch("core.recovery_views.NameComClient") as client_cls:
            recovery = self.client.post("/api/recovery/domains/a.example/plans/")
        self.assert_non_disclosing_404(recovery)
        client_cls.assert_not_called()

        with patch("core.emergency_views.NameComClient") as client_cls:
            emergency = self.client.post(
                "/api/emergency/domains/a.example/plans/",
                data=json.dumps({"targetDomain": "p3e-rescue.com"}),
                content_type="application/json",
            )
        self.assert_non_disclosing_404(emergency)
        client_cls.assert_not_called()

    def test_corrupted_derived_chains_are_excluded_from_lists_and_object_ids(self):
        self._login_a()
        self.incident_a.baseline_snapshot = self.snapshot_b
        self.incident_a.save(update_fields=["baseline_snapshot", "last_seen_at"])
        self.emergency_a.baseline_snapshot = self.snapshot_b
        self.emergency_a.save(update_fields=["baseline_snapshot", "updated_at"])

        incidents = self.client.get("/api/incidents/domains/a.example/")
        self.assertEqual(incidents.status_code, 200)
        self.assertEqual(incidents.json()["totalCount"], 0)

        recovery_list = self.client.get("/api/recovery/domains/a.example/plans/")
        self.assertEqual(recovery_list.status_code, 200)
        self.assertEqual(recovery_list.json()["totalCount"], 0)

        emergency_list = self.client.get("/api/emergency/domains/a.example/plans/")
        self.assertEqual(emergency_list.status_code, 200)
        self.assertEqual(emergency_list.json()["totalCount"], 0)

        self.assert_non_disclosing_404(
            self.client.get(f"/api/recovery/plans/{self.recovery_a.id}/")
        )
        self.assert_non_disclosing_404(
            self.client.get(f"/api/emergency/plans/{self.emergency_a.id}/")
        )

        with patch("core.recovery_views.NameComClient") as client_cls:
            preview = self.client.post("/api/recovery/domains/a.example/plans/")
        self.assert_non_disclosing_404(preview)
        client_cls.assert_not_called()
