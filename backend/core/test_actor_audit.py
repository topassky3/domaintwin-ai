from __future__ import annotations

import json

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings

from .actor_audit import (
    EMERGENCY_APPROVAL_ACTOR_EVENT,
    EMERGENCY_EXECUTION_ACTOR_EVENT,
    RECOVERY_APPROVAL_ACTOR_EVENT,
    RECOVERY_EXECUTION_ACTOR_EVENT,
    actor_snapshot,
    apply_emergency_plan_as,
    apply_recovery_plan_as,
    approve_recovery_plan_as,
)
from .emergency import create_emergency_plan
from .models import (
    DomainSnapshot,
    KnownGoodSnapshot,
    ManagedDomain,
    Membership,
    Organization,
    RecoveryPlan,
)
from .rbac import ADMIN, APPROVER, ROLE_GROUPS
from .recovery import create_recovery_plan
from .test_emergency import FakeEmergencyClient
from .test_recovery import FakeNameComClient, dns_record
from .twin import normalize_records, snapshot_fingerprint


@override_settings(DOMAIN_TWIN_TESTING=False)
class ActorAuditEvidenceTests(TestCase):
    domain = "audit.example.com"

    def setUp(self):
        User = get_user_model()
        self.approver = User.objects.create_user(username="alice-approver", password="pw")
        self.other_approver = User.objects.create_user(username="other-approver", password="pw")
        self.admin = User.objects.create_user(username="bob-admin", password="pw")

        approver_group = Group.objects.create(name=ROLE_GROUPS[APPROVER])
        admin_group = Group.objects.create(name=ROLE_GROUPS[ADMIN])
        self.approver.groups.add(approver_group)
        self.other_approver.groups.add(approver_group)
        self.admin.groups.add(admin_group)

        self.organization = Organization.objects.create(
            name="Actor audit tenant",
            slug="actor-audit-tenant",
        )
        for user, role in (
            (self.approver, Membership.Role.APPROVER),
            (self.other_approver, Membership.Role.APPROVER),
            (self.admin, Membership.Role.ADMIN),
        ):
            Membership.objects.create(
                organization=self.organization,
                user=user,
                role=role,
            )
        ManagedDomain.objects.create(
            organization=self.organization,
            name=self.domain,
        )

        baseline_records = [dns_record(None, "A", "www", "203.0.113.10")]
        normalized = normalize_records(baseline_records)
        self.baseline = DomainSnapshot.objects.create(
            domain_name=self.domain,
            version=1,
            records=normalized,
            fingerprint=snapshot_fingerprint(normalized),
        )
        KnownGoodSnapshot.objects.create(domain_name=self.domain, snapshot=self.baseline)
        self.changed_live = [dns_record(7, "A", "www", "198.51.100.20")]

    def recovery_plan(self) -> RecoveryPlan:
        plan, _ = create_recovery_plan(
            domain_name=self.domain,
            baseline=self.baseline,
            live_raw_records=self.changed_live,
        )
        return plan

    def test_actor_snapshot_is_minimal_and_role_is_server_derived(self):
        self.assertEqual(
            actor_snapshot(self.approver),
            {
                "userId": self.approver.id,
                "username": "alice-approver",
                "role": APPROVER,
            },
        )

    def test_recovery_approval_endpoint_persists_actor_and_exposes_summary(self):
        plan = self.recovery_plan()
        original_fingerprint = plan.plan_fingerprint
        self.client.force_login(self.approver)

        response = self.client.post(
            f"/api/recovery/plans/{plan.id}/approve/",
            data=json.dumps({"approve": True}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        plan.refresh_from_db()
        self.assertEqual(plan.plan_fingerprint, original_fingerprint)
        event = plan.audit_events.get(event_type=RECOVERY_APPROVAL_ACTOR_EVENT)
        self.assertEqual(event.payload["actor"]["username"], "alice-approver")
        self.assertEqual(event.payload["actor"]["role"], APPROVER)
        self.assertEqual(event.payload["planFingerprint"], original_fingerprint)
        self.assertEqual(event.payload["targetFingerprint"], plan.target_fingerprint)
        self.assertEqual(response.json()["plan"]["approvedActor"], event.payload["actor"])

    def test_recovery_approval_actor_is_not_rewritten_by_idempotent_reapproval(self):
        plan = self.recovery_plan()
        approve_recovery_plan_as(plan, user=self.approver)
        approve_recovery_plan_as(plan, user=self.other_approver)

        events = plan.audit_events.filter(event_type=RECOVERY_APPROVAL_ACTOR_EVENT)
        self.assertEqual(events.count(), 1)
        self.assertEqual(events.get().payload["actor"]["username"], "alice-approver")

    def test_recovery_execution_records_admin_before_apply_without_changing_fingerprint(self):
        plan = self.recovery_plan()
        approve_recovery_plan_as(plan, user=self.approver)
        original_fingerprint = plan.plan_fingerprint

        result = apply_recovery_plan_as(
            plan,
            user=self.admin,
            client=FakeNameComClient(self.changed_live),
        )

        result.refresh_from_db()
        self.assertEqual(result.status, RecoveryPlan.Status.RECOVERED)
        self.assertEqual(result.plan_fingerprint, original_fingerprint)
        event = result.audit_events.get(event_type=RECOVERY_EXECUTION_ACTOR_EVENT)
        self.assertEqual(event.payload["actor"]["username"], "bob-admin")
        self.assertEqual(event.payload["actor"]["role"], ADMIN)
        self.assertEqual(event.payload["planFingerprint"], original_fingerprint)
        self.assertLess(
            event.sequence,
            result.audit_events.get(event_type="APPLY_STARTED").sequence,
        )

    def test_emergency_approval_endpoint_persists_actor_without_changing_fingerprint(self):
        target = "rescue-audit.com"
        client = FakeEmergencyClient(target=target)
        plan, _ = create_emergency_plan(
            source_domain=self.domain,
            target_domain=target,
            client=client,
        )
        original_fingerprint = plan.plan_fingerprint
        self.client.force_login(self.approver)

        response = self.client.post(
            f"/api/emergency/plans/{plan.id}/approve/",
            data=json.dumps({"approve": True}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        plan.refresh_from_db()
        self.assertEqual(plan.plan_fingerprint, original_fingerprint)
        event = plan.audit_events.get(event_type=EMERGENCY_APPROVAL_ACTOR_EVENT)
        self.assertEqual(event.payload["actor"]["username"], "alice-approver")
        self.assertEqual(event.payload["actor"]["role"], APPROVER)
        self.assertEqual(event.payload["planFingerprint"], original_fingerprint)
        self.assertEqual(response.json()["plan"]["approvedActor"], event.payload["actor"])

    def test_emergency_execution_records_admin_before_registration_and_verification(self):
        target = "rescue-execute.com"
        client = FakeEmergencyClient(target=target)
        plan, _ = create_emergency_plan(
            source_domain=self.domain,
            target_domain=target,
            client=client,
        )
        approve_recovery_fingerprint = plan.plan_fingerprint
        from .actor_audit import approve_emergency_plan_as

        approve_emergency_plan_as(plan, user=self.approver)
        result = apply_emergency_plan_as(plan, user=self.admin, client=client)

        result.refresh_from_db()
        self.assertEqual(result.plan_fingerprint, approve_recovery_fingerprint)
        event = result.audit_events.get(event_type=EMERGENCY_EXECUTION_ACTOR_EVENT)
        self.assertEqual(event.payload["actor"]["username"], "bob-admin")
        self.assertEqual(event.payload["actor"]["role"], ADMIN)
        self.assertEqual(event.payload["planFingerprint"], approve_recovery_fingerprint)
        self.assertLess(
            event.sequence,
            result.audit_events.get(event_type="REGISTRATION_STARTED").sequence,
        )
        self.assertTrue(result.verification["matched"])
