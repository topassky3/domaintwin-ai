from __future__ import annotations

from unittest.mock import patch

from django.test import TestCase, override_settings

from .ai import (
    AIUnavailable,
    ProviderResult,
    SYSTEM_PROMPT,
    build_evidence_bundle,
    generate_incident_explanation,
    validate_analysis,
)
from .models import DomainSnapshot, Incident, IncidentExplanation


VALID_ANALYSIS = {
    "probable_cause": "The evidence suggests the web routing change is probably related to the availability failure.",
    "affected_service": "MULTIPLE",
    "evidence_refs": ["DNS-001", "HEALTH-HTTP", "RISK-SCORE"],
    "recommended_action": "Review the deterministic recovery preview and require human approval before restoring the known-good DNS state.",
    "confidence": {
        "level": "HIGH",
        "reason": "The DNS drift and failed health checks are directly present in the incident evidence.",
    },
}


class FakeExplainer:
    provider_name = "fake"
    model = "fake-model"

    def __init__(self, analysis=None):
        self.analysis = analysis or VALID_ANALYSIS
        self.calls = 0

    def generate(self, evidence_bundle, allowed_evidence_ids):
        self.calls += 1
        return ProviderResult(
            analysis=self.analysis,
            request_id="fake-request-1",
            latency_ms=12,
        )


class UnavailableExplainer:
    provider_name = "offline"
    model = "offline-model"

    def generate(self, evidence_bundle, allowed_evidence_ids):
        raise AIUnavailable("provider offline")


class AIExplanationTests(TestCase):
    def setUp(self):
        self.snapshot = DomainSnapshot.objects.create(
            domain_name="example.com",
            version=1,
            records=[
                {"type": "A", "host": "www", "answer": "203.0.113.10", "ttl": 300, "priority": 0}
            ],
            fingerprint="a" * 64,
        )
        self.incident = Incident.objects.create(
            domain_name="example.com",
            baseline_snapshot=self.snapshot,
            status=Incident.Status.OPEN,
            score=75,
            severity="CRITICAL",
            factors=[
                {
                    "ruleId": "ADDRESS_RECORD_CHANGED",
                    "points": 30,
                    "reason": "A routing record for www changed (MODIFIED).",
                    "state": "MODIFIED",
                    "recordType": "A",
                    "host": "www",
                    "before": {"type": "A", "host": "www", "answer": "203.0.113.10", "ttl": 300, "priority": 0},
                    "after": {"type": "A", "host": "www", "answer": "198.51.100.20", "ttl": 300, "priority": 0},
                },
                {
                    "ruleId": "HTTP_HEALTH_FAILED",
                    "points": 30,
                    "reason": "HTTP health check failed.",
                    "state": None,
                    "recordType": None,
                    "host": None,
                    "before": None,
                    "after": None,
                },
                {
                    "ruleId": "UNKNOWN_DESTINATION",
                    "points": 15,
                    "reason": "DNS points to a destination that is not recognized as trusted.",
                    "state": None,
                    "recordType": None,
                    "host": None,
                    "before": None,
                    "after": None,
                },
            ],
            evidence={
                "baseline": {"snapshotId": self.snapshot.id, "version": 1, "fingerprint": "a" * 64},
                "liveFingerprint": "b" * 64,
                "diff": {
                    "summary": {"ADDED": 0, "REMOVED": 0, "MODIFIED": 1, "UNCHANGED": 0},
                    "changes": [
                        {
                            "state": "MODIFIED",
                            "before": {"type": "A", "host": "www", "answer": "203.0.113.10", "ttl": 300, "priority": 0},
                            "after": {"type": "A", "host": "www", "answer": "198.51.100.20", "ttl": 300, "priority": 0},
                        }
                    ],
                },
                "health": {
                    "observationId": 1,
                    "checkedAt": "2026-08-19T12:00:00+00:00",
                    "dnsResolution": {"ok": False, "addresses": [], "error": "DNS resolution failed: test"},
                    "http": {"ok": False, "statusCode": None, "error": "HTTP failed", "url": "http://example.com/"},
                    "https": {"ok": False, "statusCode": None, "error": "HTTPS failed", "url": "https://example.com/"},
                    "availabilityOk": False,
                    "availabilityFailed": True,
                },
                "unknownDestination": True,
                "riskRuleVersion": "1.0",
            },
            evidence_fingerprint="c" * 64,
        )

    def test_build_evidence_bundle_uses_only_approved_input_categories(self):
        bundle, _catalog = build_evidence_bundle(self.incident)
        expected = {
            "incident_id",
            "domain_name",
            "evidence_fingerprint",
            "previous_state",
            "current_state",
            "dns_diff",
            "health_checks",
            "risk_score",
            "timestamps",
            "evidence_catalog",
        }
        self.assertEqual(set(bundle), expected)
        self.assertNotIn("recovery_plan", bundle)
        self.assertNotIn("credentials", bundle)

    def test_previous_and_current_state_are_grounded_in_incident_evidence(self):
        bundle, _ = build_evidence_bundle(self.incident)
        self.assertEqual(bundle["previous_state"]["records"][0]["answer"], "203.0.113.10")
        self.assertEqual(bundle["current_state"]["records"][0]["answer"], "198.51.100.20")
        self.assertEqual(bundle["risk_score"]["score"], 75)

    def test_evidence_catalog_has_deterministic_ids(self):
        _bundle, catalog = build_evidence_bundle(self.incident)
        ids = [item["id"] for item in catalog]
        self.assertIn("DNS-001", ids)
        self.assertIn("HEALTH-HTTP", ids)
        self.assertIn("HEALTH-HTTPS", ids)
        self.assertIn("RISK-SCORE", ids)

    def test_system_prompt_forbids_invented_dns_and_direct_mutation(self):
        lower = SYSTEM_PROMPT.lower()
        self.assertIn("never invent a dns change", lower)
        self.assertIn("never emit api calls", lower)
        self.assertIn("human-approved", lower)

    def test_validate_analysis_accepts_only_known_evidence_refs(self):
        result = validate_analysis(VALID_ANALYSIS, {"DNS-001", "HEALTH-HTTP", "RISK-SCORE"})
        self.assertEqual(result["affected_service"], "MULTIPLE")

    def test_validate_analysis_rejects_unknown_evidence_ref(self):
        invalid = {**VALID_ANALYSIS, "evidence_refs": ["DNS-999"]}
        with self.assertRaisesMessage(Exception, "does not exist"):
            validate_analysis(invalid, {"DNS-001"})

    def test_validate_analysis_rejects_extra_fields(self):
        invalid = {**VALID_ANALYSIS, "invented_fact": "something happened"}
        with self.assertRaisesMessage(Exception, "required explanation fields"):
            validate_analysis(invalid, {"DNS-001", "HEALTH-HTTP", "RISK-SCORE"})

    def test_successful_generation_is_persisted(self):
        fake = FakeExplainer()
        explanation, cached = generate_incident_explanation(self.incident, explainer=fake)
        self.assertFalse(cached)
        self.assertEqual(explanation.status, IncidentExplanation.Status.GENERATED)
        self.assertEqual(explanation.provider, "fake")
        self.assertEqual(explanation.request_id, "fake-request-1")
        self.assertEqual(explanation.analysis["evidence_refs"], VALID_ANALYSIS["evidence_refs"])

    def test_same_evidence_reuses_cached_generated_explanation(self):
        fake = FakeExplainer()
        first, first_cached = generate_incident_explanation(self.incident, explainer=fake)
        second, second_cached = generate_incident_explanation(self.incident, explainer=fake)
        self.assertFalse(first_cached)
        self.assertTrue(second_cached)
        self.assertEqual(first.id, second.id)
        self.assertEqual(fake.calls, 1)

    def test_force_regenerates_same_evidence_without_new_row(self):
        fake = FakeExplainer()
        first, _ = generate_incident_explanation(self.incident, explainer=fake)
        second, cached = generate_incident_explanation(self.incident, explainer=fake, force=True)
        self.assertFalse(cached)
        self.assertEqual(first.id, second.id)
        self.assertEqual(fake.calls, 2)
        self.assertEqual(IncidentExplanation.objects.count(), 1)

    def test_invalid_provider_evidence_reference_is_quarantined(self):
        invalid = {**VALID_ANALYSIS, "evidence_refs": ["DNS-NOT-REAL"]}
        explanation, _ = generate_incident_explanation(
            self.incident,
            explainer=FakeExplainer(invalid),
        )
        self.assertEqual(explanation.status, IncidentExplanation.Status.INVALID)
        self.assertIn("does not exist", explanation.error_message)
        self.assertEqual(explanation.analysis["probable_cause"], "AI analysis unavailable; no probable cause was generated.")

    def test_unavailable_provider_returns_explicit_fallback(self):
        explanation, cached = generate_incident_explanation(
            self.incident,
            explainer=UnavailableExplainer(),
        )
        self.assertFalse(cached)
        self.assertEqual(explanation.status, IncidentExplanation.Status.UNAVAILABLE)
        self.assertEqual(explanation.analysis["affected_service"], "UNKNOWN")
        self.assertIn("provider offline", explanation.error_message)

    @override_settings(AI_PROVIDER="disabled")
    def test_post_with_ai_disabled_keeps_endpoint_operational(self):
        response = self.client.post(f"/api/ai/incidents/{self.incident.id}/explanation/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()["analysis"]
        self.assertEqual(payload["status"], "UNAVAILABLE")
        self.assertFalse(payload["aiAvailable"])
        self.assertFalse(payload["cached"])
        self.assertTrue(payload["safety"]["factsComeFromDeterministicEvidence"])
        self.assertFalse(payload["safety"]["aiCanMutateDns"])
        self.assertTrue(payload["safety"]["humanApprovalStillRequired"])

    def test_get_before_generation_returns_not_generated_with_facts(self):
        response = self.client.get(f"/api/ai/incidents/{self.incident.id}/explanation/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()["analysis"]
        self.assertEqual(payload["status"], "NOT_GENERATED")
        self.assertFalse(payload["aiAvailable"])
        self.assertIn("inputContract", payload)
        self.assertGreater(len(payload["evidence"]), 0)

    @patch("core.ai_views.generate_incident_explanation")
    def test_successful_post_serializes_grounded_evidence_and_safety(self, mocked_generate):
        explanation = IncidentExplanation.objects.create(
            incident=self.incident,
            evidence_fingerprint=self.incident.evidence_fingerprint,
            provider="fake",
            model="fake-model",
            status=IncidentExplanation.Status.GENERATED,
            analysis=VALID_ANALYSIS,
            evidence_catalog=build_evidence_bundle(self.incident)[1],
            request_id="request-123",
            latency_ms=15,
        )
        mocked_generate.return_value = (explanation, False)
        response = self.client.post(f"/api/ai/incidents/{self.incident.id}/explanation/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()["analysis"]
        self.assertEqual(payload["status"], "GENERATED")
        self.assertTrue(payload["aiAvailable"])
        self.assertEqual(payload["label"], "Evidence-based AI analysis")
        self.assertEqual([item["id"] for item in payload["evidence"]], VALID_ANALYSIS["evidence_refs"])
        self.assertFalse(payload["safety"]["aiCanMutateDns"])

    @patch("core.ai_views.generate_incident_explanation")
    def test_get_after_generation_returns_cached_generated_output(self, mocked_generate):
        explanation = IncidentExplanation.objects.create(
            incident=self.incident,
            evidence_fingerprint=self.incident.evidence_fingerprint,
            provider="fake",
            model="fake-model",
            status=IncidentExplanation.Status.GENERATED,
            analysis=VALID_ANALYSIS,
            evidence_catalog=build_evidence_bundle(self.incident)[1],
            request_id="request-123",
            latency_ms=15,
        )
        response = self.client.get(f"/api/ai/incidents/{self.incident.id}/explanation/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()["analysis"]
        self.assertEqual(payload["status"], "GENERATED")
        self.assertTrue(payload["cached"])
        mocked_generate.assert_not_called()
        self.assertEqual(explanation.id, payload["explanationId"])

    def test_incident_not_found_returns_404(self):
        response = self.client.get("/api/ai/incidents/999999/explanation/")
        self.assertEqual(response.status_code, 404)
