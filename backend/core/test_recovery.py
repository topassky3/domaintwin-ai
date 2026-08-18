from __future__ import annotations

from copy import deepcopy
from unittest.mock import patch

from django.test import TestCase

from .models import DomainSnapshot, Incident, KnownGoodSnapshot, RecoveryPlan
from .namecom import NameComAPIError
from .recovery import (
    RecoveryApprovalRequired,
    RecoveryStalePlan,
    apply_recovery_plan,
    approve_recovery_plan,
    build_recovery_operations,
    create_recovery_plan,
)
from .twin import normalize_records, snapshot_fingerprint


def dns_record(
    record_id: int | None,
    record_type: str,
    host: str,
    answer: str,
    *,
    ttl: int = 300,
    priority: int = 0,
) -> dict:
    record = {
        "type": record_type,
        "host": host,
        "answer": answer,
        "ttl": ttl,
        "priority": priority,
    }
    if record_id is not None:
        record["id"] = record_id
    return record


class FakeNameComClient:
    def __init__(
        self,
        records: list[dict],
        *,
        fail_mutation_number: int | None = None,
        fail_status: int = 503,
        force_verification_records: list[dict] | None = None,
    ):
        self.records = deepcopy(records)
        self.fail_mutation_number = fail_mutation_number
        self.fail_status = fail_status
        self.force_verification_records = deepcopy(force_verification_records)
        self.mutation_calls = 0
        self.list_calls = 0
        self.next_id = max([int(row.get("id") or 0) for row in self.records] + [100]) + 1

    def list_records(self, domain_name: str) -> dict:
        self.list_calls += 1
        if self.force_verification_records is not None and self.list_calls >= 2:
            return {"records": deepcopy(self.force_verification_records)}
        return {"records": deepcopy(self.records)}

    def _before_mutation(self):
        self.mutation_calls += 1
        if self.fail_mutation_number == self.mutation_calls:
            raise NameComAPIError(
                status_code=self.fail_status,
                message="controlled provider failure",
                retryable=True,
            )

    def update_record(self, domain_name: str, record_id: int, payload: dict) -> dict:
        self._before_mutation()
        for index, row in enumerate(self.records):
            if int(row.get("id")) == int(record_id):
                self.records[index] = {**row, **payload, "id": record_id}
                return deepcopy(self.records[index])
        raise NameComAPIError(status_code=404, message="record not found")

    def create_record(self, domain_name: str, payload: dict) -> dict:
        self._before_mutation()
        row = {**payload, "id": self.next_id}
        self.next_id += 1
        self.records.append(row)
        return deepcopy(row)

    def delete_record(self, domain_name: str, record_id: int) -> dict:
        self._before_mutation()
        before = len(self.records)
        self.records = [row for row in self.records if int(row.get("id")) != int(record_id)]
        if len(self.records) == before:
            raise NameComAPIError(status_code=404, message="record not found")
        return {}


class RecoveryTestBase(TestCase):
    domain = "demo.example.com"

    def snapshot(self, records: list[dict], *, version: int = 1) -> DomainSnapshot:
        normalized = normalize_records(records)
        return DomainSnapshot.objects.create(
            domain_name=self.domain,
            version=version,
            records=normalized,
            fingerprint=snapshot_fingerprint(normalized),
        )

    def incident(self, baseline: DomainSnapshot) -> Incident:
        return Incident.objects.create(
            domain_name=self.domain,
            baseline_snapshot=baseline,
            score=75,
            severity="CRITICAL",
            factors=[{"ruleId": "ADDRESS_RECORD_CHANGED", "points": 30}],
            evidence={"demo": True},
            evidence_fingerprint="a" * 64,
        )


class RecoveryPlannerTests(RecoveryTestBase):
    def test_modified_record_becomes_update_with_provider_id(self):
        baseline = [dns_record(None, "A", "www", "203.0.113.10")]
        live = [dns_record(42, "A", "www", "198.51.100.20")]
        operations = build_recovery_operations(baseline, live)
        self.assertEqual(len(operations), 1)
        self.assertEqual(operations[0]["action"], "UPDATE")
        self.assertEqual(operations[0]["recordId"], 42)
        self.assertEqual(operations[0]["before"]["answer"], "198.51.100.20")
        self.assertEqual(operations[0]["after"]["answer"], "203.0.113.10")

    def test_missing_and_unexpected_records_become_create_then_delete(self):
        baseline = [dns_record(None, "MX", "@", "mail.example.com", priority=10)]
        live = [dns_record(9, "TXT", "tmp", "unexpected")]
        operations = build_recovery_operations(baseline, live)
        self.assertEqual([row["action"] for row in operations], ["CREATE", "DELETE"])
        self.assertEqual(operations[0]["after"]["type"], "MX")
        self.assertEqual(operations[1]["recordId"], 9)

    def test_exact_records_generate_no_operations(self):
        baseline = [dns_record(None, "A", "www", "203.0.113.10")]
        live = [dns_record(7, "A", "www", "203.0.113.10")]
        self.assertEqual(build_recovery_operations(baseline, live), [])

    def test_plan_is_deterministic_and_reused_while_active(self):
        baseline = self.snapshot([dns_record(None, "A", "www", "203.0.113.10")])
        live = [dns_record(7, "A", "www", "198.51.100.20")]
        plan_a, created_a = create_recovery_plan(
            domain_name=self.domain,
            baseline=baseline,
            live_raw_records=live,
        )
        plan_b, created_b = create_recovery_plan(
            domain_name=self.domain,
            baseline=baseline,
            live_raw_records=list(reversed(live)),
        )
        self.assertTrue(created_a)
        self.assertFalse(created_b)
        self.assertEqual(plan_a.id, plan_b.id)
        self.assertEqual(plan_a.plan_fingerprint, plan_b.plan_fingerprint)

    def test_explicit_approval_is_idempotent(self):
        baseline = self.snapshot([dns_record(None, "A", "www", "203.0.113.10")])
        plan, _ = create_recovery_plan(
            domain_name=self.domain,
            baseline=baseline,
            live_raw_records=[dns_record(7, "A", "www", "198.51.100.20")],
        )
        approve_recovery_plan(plan)
        approve_recovery_plan(plan)
        plan.refresh_from_db()
        self.assertEqual(plan.status, RecoveryPlan.Status.APPROVED)
        self.assertIsNotNone(plan.approved_at)
        self.assertEqual(plan.audit_events.filter(event_type="PLAN_APPROVED").count(), 1)

    def test_failed_plan_can_be_replanned_as_fresh_attempt(self):
        baseline = self.snapshot([dns_record(None, "A", "www", "203.0.113.10")])
        live = [dns_record(7, "A", "www", "198.51.100.20")]
        first, _ = create_recovery_plan(
            domain_name=self.domain,
            baseline=baseline,
            live_raw_records=live,
        )
        first.status = RecoveryPlan.Status.FAILED
        first.save(update_fields=["status", "updated_at"])
        second, created = create_recovery_plan(
            domain_name=self.domain,
            baseline=baseline,
            live_raw_records=live,
        )
        self.assertTrue(created)
        self.assertNotEqual(first.id, second.id)


class RecoveryApplyTests(RecoveryTestBase):
    def test_apply_requires_prior_approval(self):
        baseline = self.snapshot([dns_record(None, "A", "www", "203.0.113.10")])
        live = [dns_record(7, "A", "www", "198.51.100.20")]
        plan, _ = create_recovery_plan(
            domain_name=self.domain,
            baseline=baseline,
            live_raw_records=live,
        )
        with self.assertRaises(RecoveryApprovalRequired):
            apply_recovery_plan(plan, client=FakeNameComClient(live))

    def test_successful_apply_verifies_and_resolves_incident(self):
        baseline = self.snapshot([dns_record(None, "A", "www", "203.0.113.10")])
        incident = self.incident(baseline)
        live = [dns_record(7, "A", "www", "198.51.100.20")]
        plan, _ = create_recovery_plan(
            domain_name=self.domain,
            baseline=baseline,
            live_raw_records=live,
            incident=incident,
        )
        approve_recovery_plan(plan)
        client = FakeNameComClient(live)
        result = apply_recovery_plan(plan, client=client)
        result.refresh_from_db()
        incident.refresh_from_db()
        self.assertEqual(result.status, RecoveryPlan.Status.RECOVERED)
        self.assertTrue(result.verification["matched"])
        self.assertEqual(client.mutation_calls, 1)
        self.assertEqual(incident.status, Incident.Status.RESOLVED)
        event_types = list(incident.timeline.values_list("event_type", flat=True))
        self.assertIn("RECOVERY_VERIFIED", event_types)
        self.assertEqual(event_types[-1], "INCIDENT_RESOLVED")

    def test_reapply_recovered_plan_is_idempotent_without_provider_calls(self):
        baseline = self.snapshot([dns_record(None, "A", "www", "203.0.113.10")])
        live = [dns_record(7, "A", "www", "198.51.100.20")]
        plan, _ = create_recovery_plan(
            domain_name=self.domain,
            baseline=baseline,
            live_raw_records=live,
        )
        approve_recovery_plan(plan)
        client = FakeNameComClient(live)
        apply_recovery_plan(plan, client=client)
        calls_after_first = client.mutation_calls
        apply_recovery_plan(plan, client=client)
        self.assertEqual(client.mutation_calls, calls_after_first)

    def test_already_recovered_live_state_skips_mutation(self):
        baseline_records = [dns_record(None, "A", "www", "203.0.113.10")]
        baseline = self.snapshot(baseline_records)
        changed = [dns_record(7, "A", "www", "198.51.100.20")]
        plan, _ = create_recovery_plan(
            domain_name=self.domain,
            baseline=baseline,
            live_raw_records=changed,
        )
        approve_recovery_plan(plan)
        already_good = [dns_record(7, "A", "www", "203.0.113.10")]
        client = FakeNameComClient(already_good)
        result = apply_recovery_plan(plan, client=client)
        self.assertEqual(result.status, RecoveryPlan.Status.RECOVERED)
        self.assertEqual(client.mutation_calls, 0)
        self.assertTrue(
            result.audit_events.filter(event_type="APPLY_SKIPPED_ALREADY_RECOVERED").exists()
        )

    def test_live_change_after_preview_marks_plan_stale(self):
        baseline = self.snapshot([dns_record(None, "A", "www", "203.0.113.10")])
        preview_live = [dns_record(7, "A", "www", "198.51.100.20")]
        plan, _ = create_recovery_plan(
            domain_name=self.domain,
            baseline=baseline,
            live_raw_records=preview_live,
        )
        approve_recovery_plan(plan)
        changed_again = [dns_record(7, "A", "www", "192.0.2.99")]
        with self.assertRaises(RecoveryStalePlan):
            apply_recovery_plan(plan, client=FakeNameComClient(changed_again))
        plan.refresh_from_db()
        self.assertEqual(plan.status, RecoveryPlan.Status.STALE)
        self.assertFalse(plan.verification["matched"])

    def test_failure_after_first_operation_is_partial_recovery(self):
        baseline = self.snapshot(
            [
                dns_record(None, "A", "www", "203.0.113.10"),
                dns_record(None, "TXT", "required", "good"),
            ]
        )
        live = [
            dns_record(7, "A", "www", "198.51.100.20"),
            dns_record(8, "TXT", "temp", "remove-me"),
        ]
        plan, _ = create_recovery_plan(
            domain_name=self.domain,
            baseline=baseline,
            live_raw_records=live,
        )
        approve_recovery_plan(plan)
        client = FakeNameComClient(live, fail_mutation_number=2)
        result = apply_recovery_plan(plan, client=client)
        self.assertEqual(result.status, RecoveryPlan.Status.PARTIAL)
        self.assertEqual(result.operation_results[0]["status"], "SUCCEEDED")
        self.assertEqual(result.operation_results[1]["status"], "FAILED")
        self.assertEqual(client.mutation_calls, 2)

    def test_failure_on_first_operation_is_failed_not_false_success(self):
        baseline = self.snapshot([dns_record(None, "A", "www", "203.0.113.10")])
        live = [dns_record(7, "A", "www", "198.51.100.20")]
        plan, _ = create_recovery_plan(
            domain_name=self.domain,
            baseline=baseline,
            live_raw_records=live,
        )
        approve_recovery_plan(plan)
        result = apply_recovery_plan(
            plan,
            client=FakeNameComClient(live, fail_mutation_number=1),
        )
        self.assertEqual(result.status, RecoveryPlan.Status.FAILED)
        self.assertEqual(result.operation_results[0]["status"], "FAILED")

    def test_verification_mismatch_becomes_partial(self):
        baseline = self.snapshot([dns_record(None, "A", "www", "203.0.113.10")])
        live = [dns_record(7, "A", "www", "198.51.100.20")]
        wrong_after = [dns_record(7, "A", "www", "192.0.2.55")]
        plan, _ = create_recovery_plan(
            domain_name=self.domain,
            baseline=baseline,
            live_raw_records=live,
        )
        approve_recovery_plan(plan)
        client = FakeNameComClient(live, force_verification_records=wrong_after)
        result = apply_recovery_plan(plan, client=client)
        self.assertEqual(result.status, RecoveryPlan.Status.PARTIAL)
        self.assertFalse(result.verification["matched"])
        self.assertTrue(result.audit_events.filter(event_type="VERIFICATION_FAILED").exists())


class RecoveryEndpointTests(RecoveryTestBase):
    def setUp(self):
        self.baseline = self.snapshot([dns_record(None, "A", "www", "203.0.113.10")])
        KnownGoodSnapshot.objects.create(domain_name=self.domain, snapshot=self.baseline)
        self.live = [dns_record(7, "A", "www", "198.51.100.20")]

    @patch("core.recovery_views.NameComClient")
    def test_preview_endpoint_returns_exact_update_without_mutating(self, client_cls):
        fake = FakeNameComClient(self.live)
        client_cls.return_value = fake
        response = self.client.post(f"/api/recovery/domains/{self.domain}/plans/")
        self.assertEqual(response.status_code, 201)
        payload = response.json()["plan"]
        self.assertEqual(payload["status"], "PREVIEW")
        self.assertTrue(payload["requiresApproval"])
        self.assertEqual(payload["operations"][0]["action"], "UPDATE")
        self.assertEqual(payload["operations"][0]["recordId"], 7)
        self.assertEqual(fake.mutation_calls, 0)

    @patch("core.recovery_views.NameComClient")
    def test_approval_endpoint_requires_literal_true(self, client_cls):
        client_cls.return_value = FakeNameComClient(self.live)
        preview = self.client.post(f"/api/recovery/domains/{self.domain}/plans/").json()
        plan_id = preview["plan"]["id"]
        denied = self.client.post(
            f"/api/recovery/plans/{plan_id}/approve/",
            data={"approve": False},
            content_type="application/json",
        )
        self.assertEqual(denied.status_code, 400)
        approved = self.client.post(
            f"/api/recovery/plans/{plan_id}/approve/",
            data={"approve": True},
            content_type="application/json",
        )
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.json()["plan"]["status"], "APPROVED")

    @patch("core.recovery.NameComClient")
    @patch("core.recovery_views.NameComClient")
    def test_full_preview_approve_apply_endpoint_flow(self, preview_client_cls, apply_client_cls):
        fake = FakeNameComClient(self.live)
        preview_client_cls.return_value = fake
        apply_client_cls.return_value = fake
        preview = self.client.post(f"/api/recovery/domains/{self.domain}/plans/").json()
        plan_id = preview["plan"]["id"]
        self.client.post(
            f"/api/recovery/plans/{plan_id}/approve/",
            data={"approve": True},
            content_type="application/json",
        )
        applied = self.client.post(f"/api/recovery/plans/{plan_id}/apply/")
        self.assertEqual(applied.status_code, 200)
        payload = applied.json()["plan"]
        self.assertEqual(payload["status"], "RECOVERED")
        self.assertTrue(payload["verification"]["matched"])
        self.assertEqual(payload["operationResults"][0]["status"], "SUCCEEDED")
        self.assertEqual(
            [event["sequence"] for event in payload["audit"]],
            list(range(1, len(payload["audit"]) + 1)),
        )

    @patch("core.recovery_views.NameComClient")
    def test_open_incident_baseline_is_used_for_preview(self, client_cls):
        newer = self.snapshot([dns_record(None, "A", "www", "192.0.2.10")], version=2)
        marker = KnownGoodSnapshot.objects.get(domain_name=self.domain)
        marker.snapshot = newer
        marker.save()
        incident = self.incident(self.baseline)
        client_cls.return_value = FakeNameComClient(self.live)
        response = self.client.post(f"/api/recovery/domains/{self.domain}/plans/")
        payload = response.json()["plan"]
        self.assertEqual(payload["incidentId"], incident.id)
        self.assertEqual(payload["baselineSnapshotId"], self.baseline.id)
        self.assertEqual(payload["operations"][0]["after"]["answer"], "203.0.113.10")
