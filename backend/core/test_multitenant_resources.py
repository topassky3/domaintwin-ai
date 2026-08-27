from __future__ import annotations

import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings

from .models import (
    DomainSnapshot,
    EmergencyDomainPlan,
    Incident,
    ManagedDomain,
    Membership,
    Organization,
    RecoveryPlan,
)
from .rbac import ADMIN, ROLE_GROUPS


@override_settings(DOMAIN_TWIN_TESTING=False)
class TenantDerivedResourceBoundaryTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="p3c-admin", password="pw")
        admin_group, _ = Group.objects.get_or_create(name=ROLE_GROUPS[ADMIN])
        self.user.groups.add(admin_group)

        self.org_a = Organization.objects.create(name="Tenant A", slug="p3c-a")
        self.org_b = Organization.objects.create(name="Tenant B", slug="p3c-b")
        for organization in (self.org_a, self.org_b):
            Membership.objects.create(
                organization=organization,
                user=self.user,
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
            records=[],
            fingerprint="a" * 64,
        )
        self.snapshot_b = DomainSnapshot.objects.create(
            domain_name="b.example",
            version=1,
            records=[],
            fingerprint="b" * 64,
        )
        self.incident_a = Incident.objects.create(
            domain_name="a.example",
            baseline_snapshot=self.snapshot_a,
            score=80,
            severity="HIGH",
            factors=[],
            evidence={},
            evidence_fingerprint="1" * 64,
        )
        self.incident_b = Incident.objects.create(
            domain_name="b.example",
            baseline_snapshot=self.snapshot_b,
            score=80,
            severity="HIGH",
            factors=[],
            evidence={},
            evidence_fingerprint="2" * 64,
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
            operations=[],
        )
        self.emergency_a = EmergencyDomainPlan.objects.create(
            source_domain_name="a.example",
            target_domain_name="a-emergency.example",
            baseline_snapshot=self.snapshot_a,
            expected_fingerprint="a" * 64,
            plan_fingerprint="7" * 64,
            idempotency_key="p3c-a-emergency",
            operations=[],
        )
        self.emergency_b = EmergencyDomainPlan.objects.create(
            source_domain_name="b.example",
            target_domain_name="b-emergency.example",
            baseline_snapshot=self.snapshot_b,
            expected_fingerprint="b" * 64,
            plan_fingerprint="8" * 64,
            idempotency_key="p3c-b-emergency",
            operations=[],
        )

        self.client.force_login(self.user)
        response = self.client.post(
            "/api/auth/active-organization/",
            data=json.dumps({"organizationId": str(self.org_a.id)}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

    def assert_non_disclosing_404(self, response):
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["message"], "Resource not found.")

    def test_same_tenant_object_ids_remain_readable(self):
        for url in (
            f"/api/incidents/{self.incident_a.id}/",
            f"/api/recovery/plans/{self.recovery_a.id}/",
            f"/api/emergency/plans/{self.emergency_a.id}/",
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

    def test_cross_tenant_incident_and_ai_ids_fail_before_ai_execution(self):
        response = self.client.get(f"/api/incidents/{self.incident_b.id}/")
        self.assert_non_disclosing_404(response)

        with patch("core.ai_views.generate_incident_explanation") as generate, patch(
            "core.ai_views.build_evidence_bundle"
        ) as build_bundle:
            response = self.client.post(
                f"/api/ai/incidents/{self.incident_b.id}/explanation/"
            )
        self.assert_non_disclosing_404(response)
        generate.assert_not_called()
        build_bundle.assert_not_called()

    def test_cross_tenant_recovery_ids_fail_before_approval_or_apply(self):
        with patch("core.recovery_views.approve_recovery_plan_as") as approve:
            response = self.client.post(
                f"/api/recovery/plans/{self.recovery_b.id}/approve/",
                data=json.dumps({"approve": True}),
                content_type="application/json",
            )
        self.assert_non_disclosing_404(response)
        approve.assert_not_called()

        with patch("core.recovery_views.apply_recovery_plan_as") as apply_plan:
            response = self.client.post(f"/api/recovery/plans/{self.recovery_b.id}/apply/")
        self.assert_non_disclosing_404(response)
        apply_plan.assert_not_called()

    def test_cross_tenant_emergency_ids_fail_before_provider_or_mutation(self):
        with patch("core.emergency_views.approve_emergency_plan_as") as approve:
            response = self.client.post(
                f"/api/emergency/plans/{self.emergency_b.id}/approve/",
                data=json.dumps({"approve": True}),
                content_type="application/json",
            )
        self.assert_non_disclosing_404(response)
        approve.assert_not_called()

        with patch("core.emergency_views.NameComClient") as client_cls, patch(
            "core.emergency_views.apply_emergency_plan_as"
        ) as apply_plan:
            response = self.client.post(
                f"/api/emergency/plans/{self.emergency_b.id}/apply/",
                data=json.dumps(
                    {
                        "execute": True,
                        "targetDomain": self.emergency_b.target_domain_name,
                    }
                ),
                content_type="application/json",
            )
        self.assert_non_disclosing_404(response)
        client_cls.assert_not_called()
        apply_plan.assert_not_called()

    def test_mismatched_resource_and_baseline_tenant_fails_closed(self):
        inconsistent = RecoveryPlan.objects.create(
            domain_name="a.example",
            baseline_snapshot=self.snapshot_b,
            live_fingerprint_before="9" * 64,
            target_fingerprint="a" * 64,
            plan_fingerprint="0" * 64,
            operations=[],
        )
        response = self.client.get(f"/api/recovery/plans/{inconsistent.id}/")
        self.assert_non_disclosing_404(response)
