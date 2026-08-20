from __future__ import annotations

import io
import json
from copy import deepcopy
from urllib import error
from unittest.mock import patch

from django.test import TestCase, override_settings

from .models import DomainSnapshot, Incident, IncidentExplanation, RecoveryPlan
from .namecom import NameComAPIError, NameComClient
from .recovery import RecoveryStalePlan, apply_recovery_plan, approve_recovery_plan, create_recovery_plan
from .twin import normalize_records, snapshot_fingerprint


SAFE_NAMECOM_SETTINGS = {
    "NAMECOM_ENVIRONMENT": "sandbox",
    "NAMECOM_USERNAME": "gate9-user",
    "NAMECOM_API_TOKEN": "gate9-secret-token",
    "NAMECOM_TIMEOUT_SECONDS": 1,
    "NAMECOM_ALLOW_MUTATIONS": False,
    "NAMECOM_ALLOW_PRODUCTION_MUTATIONS": False,
    "NAMECOM_ALLOW_DOMAIN_REGISTRATION": False,
}


def dns_record(
    record_id: int | None,
    record_type: str,
    host: str,
    answer: str,
    *,
    ttl: int = 300,
    priority: int = 0,
) -> dict:
    row = {
        "type": record_type,
        "host": host,
        "answer": answer,
        "ttl": ttl,
        "priority": priority,
    }
    if record_id is not None:
        row["id"] = record_id
    return row


def http_error(status: int, payload: dict | None = None) -> error.HTTPError:
    body = json.dumps(payload or {}).encode("utf-8")
    return error.HTTPError(
        url="https://api.dev.name.com/core/v1/hello",
        code=status,
        msg=f"HTTP {status}",
        hdrs=None,
        fp=io.BytesIO(body),
    )


@override_settings(**SAFE_NAMECOM_SETTINGS)
class NameComFailureClassificationTests(TestCase):
    @patch("core.namecom.request.urlopen")
    def test_invalid_token_401_is_explicit_and_not_retryable(self, urlopen):
        urlopen.side_effect = http_error(401, {"message": "Authentication failed"})
        with self.assertRaises(NameComAPIError) as raised:
            NameComClient().hello()
        exc = raised.exception
        self.assertEqual(exc.status_code, 401)
        self.assertFalse(exc.retryable)
        self.assertEqual(exc.message, "Authentication failed")
        self.assertNotIn("gate9-secret-token", f"{exc.message} {exc.details}")

    @patch("core.namecom.request.urlopen")
    def test_rate_limit_429_is_marked_retryable(self, urlopen):
        urlopen.side_effect = http_error(429, {"message": "Rate limit exceeded"})
        with self.assertRaises(NameComAPIError) as raised:
            NameComClient().hello()
        self.assertEqual(raised.exception.status_code, 429)
        self.assertTrue(raised.exception.retryable)

    @patch("core.namecom.request.urlopen")
    def test_provider_5xx_is_marked_retryable(self, urlopen):
        urlopen.side_effect = http_error(503, {"message": "Provider unavailable"})
        with self.assertRaises(NameComAPIError) as raised:
            NameComClient().hello()
        self.assertEqual(raised.exception.status_code, 503)
        self.assertTrue(raised.exception.retryable)

    @patch("core.namecom.request.urlopen")
    def test_network_failure_is_normalized_to_retryable_503(self, urlopen):
        urlopen.side_effect = error.URLError("controlled network failure")
        with self.assertRaises(NameComAPIError) as raised:
            NameComClient().hello()
        self.assertEqual(raised.exception.status_code, 503)
        self.assertTrue(raised.exception.retryable)
        self.assertEqual(raised.exception.message, "Unable to reach name.com API.")

    @patch("core.namecom.request.urlopen")
    def test_timeout_is_normalized_to_retryable_504(self, urlopen):
        urlopen.side_effect = TimeoutError("controlled timeout")
        with self.assertRaises(NameComAPIError) as raised:
            NameComClient().hello()
        self.assertEqual(raised.exception.status_code, 504)
        self.assertTrue(raised.exception.retryable)
        self.assertEqual(raised.exception.message, "name.com API request timed out.")


class ControlledRecoveryClient:
    def __init__(
        self,
        records: list[dict],
        *,
        fail_mutation_number: int | None = None,
        fail_status: int = 503,
    ) -> None:
        self.records = deepcopy(records)
        self.fail_mutation_number = fail_mutation_number
        self.fail_status = fail_status
        self.mutation_calls = 0
        self.next_id = max([int(row.get("id") or 0) for row in self.records] + [100]) + 1

    def list_records(self, domain_name: str) -> dict:
        return {"records": deepcopy(self.records)}

    def _before_mutation(self) -> None:
        self.mutation_calls += 1
        if self.fail_mutation_number == self.mutation_calls:
            raise NameComAPIError(
                status_code=self.fail_status,
                message="controlled Gate 9 provider failure",
                retryable=self.fail_status in {429, 500, 502, 503, 504},
            )

    def update_record(self, domain_name: str, record_id: int, payload: dict) -> dict:
        self._before_mutation()
        for index, row in enumerate(self.records):
            if int(row.get("id") or 0) == int(record_id):
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
        self.records = [row for row in self.records if int(row.get("id") or 0) != int(record_id)]
        if len(self.records) == before:
            raise NameComAPIError(status_code=404, message="record not found")
        return {}


class RecoverySafetyTests(TestCase):
    domain = "gate9.example.com"

    def snapshot(self, records: list[dict]) -> DomainSnapshot:
        normalized = normalize_records(records)
        return DomainSnapshot.objects.create(
            domain_name=self.domain,
            version=1,
            records=normalized,
            fingerprint=snapshot_fingerprint(normalized),
        )

    def test_record_already_deleted_before_apply_becomes_verified_noop(self):
        baseline_records = [dns_record(None, "A", "www", "203.0.113.10")]
        preview_live = [
            dns_record(7, "A", "www", "203.0.113.10"),
            dns_record(8, "TXT", "temporary", "remove-me"),
        ]
        baseline = self.snapshot(baseline_records)
        plan, _ = create_recovery_plan(
            domain_name=self.domain,
            baseline=baseline,
            live_raw_records=preview_live,
        )
        self.assertEqual([op["action"] for op in plan.operations], ["DELETE"])
        approve_recovery_plan(plan)

        already_deleted = [dns_record(7, "A", "www", "203.0.113.10")]
        client = ControlledRecoveryClient(already_deleted)
        result = apply_recovery_plan(plan, client=client)

        self.assertEqual(result.status, RecoveryPlan.Status.RECOVERED)
        self.assertEqual(client.mutation_calls, 0)
        self.assertTrue(result.verification["matched"])
        self.assertTrue(
            result.audit_events.filter(event_type="APPLY_SKIPPED_ALREADY_RECOVERED").exists()
        )

    def test_unexpected_record_added_after_preview_marks_plan_stale_without_mutation(self):
        baseline = self.snapshot([dns_record(None, "A", "www", "203.0.113.10")])
        preview_live = [dns_record(7, "A", "www", "198.51.100.20")]
        plan, _ = create_recovery_plan(
            domain_name=self.domain,
            baseline=baseline,
            live_raw_records=preview_live,
        )
        approve_recovery_plan(plan)

        changed_again = [
            dns_record(7, "A", "www", "198.51.100.20"),
            dns_record(9, "TXT", "intruder", "unexpected-after-preview"),
        ]
        client = ControlledRecoveryClient(changed_again)
        with self.assertRaises(RecoveryStalePlan):
            apply_recovery_plan(plan, client=client)

        plan.refresh_from_db()
        self.assertEqual(plan.status, RecoveryPlan.Status.STALE)
        self.assertEqual(client.mutation_calls, 0)
        self.assertIn("regenerate recovery plan", plan.verification["reason"].lower())
        self.assertTrue(plan.audit_events.filter(event_type="PLAN_STALE").exists())

    def test_second_operation_failure_is_partial_never_false_success(self):
        baseline = self.snapshot(
            [
                dns_record(None, "A", "www", "203.0.113.10"),
                dns_record(None, "TXT", "required", "known-good"),
            ]
        )
        preview_live = [
            dns_record(7, "A", "www", "198.51.100.20"),
            dns_record(8, "TXT", "temporary", "remove-me"),
        ]
        plan, _ = create_recovery_plan(
            domain_name=self.domain,
            baseline=baseline,
            live_raw_records=preview_live,
        )
        approve_recovery_plan(plan)
        client = ControlledRecoveryClient(preview_live, fail_mutation_number=2, fail_status=503)

        result = apply_recovery_plan(plan, client=client)

        self.assertEqual(result.status, RecoveryPlan.Status.PARTIAL)
        self.assertEqual(result.operation_results[0]["status"], "SUCCEEDED")
        self.assertEqual(result.operation_results[1]["status"], "FAILED")
        self.assertEqual(result.operation_results[1]["providerStatus"], 503)
        self.assertTrue(result.operation_results[1]["retryable"])
        self.assertFalse(result.audit_events.filter(event_type="RECOVERY_COMPLETED").exists())


class AIFallbackSafetyTests(TestCase):
    @override_settings(AI_PROVIDER="disabled")
    def test_ai_unavailable_returns_safe_fallback_and_preserves_human_boundary(self):
        records = normalize_records([dns_record(None, "A", "www", "203.0.113.10")])
        snapshot = DomainSnapshot.objects.create(
            domain_name="ai-gate9.example.com",
            version=1,
            records=records,
            fingerprint=snapshot_fingerprint(records),
        )
        incident = Incident.objects.create(
            domain_name="ai-gate9.example.com",
            baseline_snapshot=snapshot,
            score=75,
            severity="CRITICAL",
            factors=[{"ruleId": "ADDRESS_RECORD_CHANGED", "points": 30}],
            evidence={"dnsDiff": {"changes": []}, "health": {}},
            evidence_fingerprint="9" * 64,
        )

        response = self.client.post(f"/api/ai/incidents/{incident.id}/explanation/")

        self.assertEqual(response.status_code, 200)
        analysis = response.json()["analysis"]
        self.assertEqual(analysis["status"], IncidentExplanation.Status.UNAVAILABLE)
        self.assertFalse(analysis["aiAvailable"])
        self.assertFalse(analysis["safety"]["aiCanMutateDns"])
        self.assertTrue(analysis["safety"]["humanApprovalStillRequired"])
        self.assertIn("AI analysis unavailable", analysis["probableCause"])
        self.assertIn("deterministic DNS diff", analysis["recommendedAction"])


class EnvironmentBoundaryTests(TestCase):
    @override_settings(
        NAMECOM_ENVIRONMENT="production",
        NAMECOM_USERNAME="gate9-prod-user",
        NAMECOM_API_TOKEN="production-placeholder-token",
        NAMECOM_TIMEOUT_SECONDS=1,
        NAMECOM_ALLOW_MUTATIONS=True,
        NAMECOM_ALLOW_PRODUCTION_MUTATIONS=False,
        NAMECOM_ALLOW_DOMAIN_REGISTRATION=False,
    )
    def test_production_has_distinct_base_url_and_mutation_requires_second_opt_in(self):
        client = NameComClient()
        self.assertEqual(client.base_url, "https://api.name.com")
        with self.assertRaises(NameComAPIError) as raised:
            client.create_record(
                "example.com",
                {"type": "A", "host": "www", "answer": "203.0.113.10", "ttl": 300},
            )
        self.assertEqual(raised.exception.status_code, 403)
        self.assertIn("explicit opt-in", raised.exception.message)
