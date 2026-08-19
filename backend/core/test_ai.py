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


class UnavailableExplainer(FakeExplainer):
    provider_name = "fake-unavailable"

    def generate(self, evidence_bundle, allowed_evidence_ids):
        self.calls += 1
        raise AIUnavailable("provider offline")


class AIExplanationTests(TestCase):
    def setUp(self):
        self.baseline = DomainSnapshot.objects.create(
            domain_name="example.com",
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
        self.incident = Incident.objects.create(
            domain_name="example.com",
            baseline_snapshot=self.baseline,
            score=75,
            severity="CRITICAL",
            factors=[
                {
                    "ruleId": "ADDRESS_RECORD_CHANGED",
                    "points": 30,
                    "reason": "A routing record for www changed (MODIFIED).",
                },
                {
                    "ruleId": "HTTP_HEALTH_FAILED",
                    "points": 30,
                    "reason": "HTTP health check failed.",
                },
                {
                    "ruleId": "UNKNOWN_DESTINATION",
                    "points": 15,
                    "reason": "DNS points to a destination that is not recognized as trusted.",
                },
            ],
            evidence={
                "baseline": {
                    "snapshotId": self.baseline.id,
                    "version": 1,
                    "fingerprint": "a" * 64,
                },
                "liveFingerprint": "b" * 64,
                "diff": {
                    "summary": {"ADDED": 0, "REMOVED": 0, "MODIFIED": 1, "UNCHANGED": 0},
                    "changes": [
                        {
                            "state": "MODIFIED",
                            "before": {
                                "type": "A",
                                "host": "www",
                                "answer": "203.0.113.10",
                                "ttl": 300,
                                "priority": 0,
                            },
                            "after": {
                                "type": "A",
                                "host": "www",
                                "answer": "198.51.100.20",
                                "ttl": 300,
                                "priority": 0,
                            },
                        }
                    ],
                },
                "health": {
                    "checkedAt": "2026-08-18T21:30:29+00:00",
                    "dnsResolution": {"ok": False, "addresses": [], "error": "DNS resolution failed"},
                    "http": {"ok": False, "statusCode": None, "error": "DNS resolution failed"},
                    "https": {"ok": False, "statusCode": None, "error": "DNS resolution failed"},
                    "availabilityOk": False,
                    "availabilityFailed": True,
                },
                "unknownDestination": True,
                "riskRuleVersion": "1.0",
            },
            evidence_fingerprint="f" * 64,
        )

    def test_bundle_contains_only_gate6_input_categories(self):
        bundle, catalog = build_evidence_bundle(self.incident)
        for key in (
            "previous_state",
            "current_state",
            "dns_diff",
            "health_checks",
            "risk_score",
            "timestamps",
        ):
            self.assertIn(key, bundle)
        self.assertNotIn("recovery_plan", bundle)
        self.assertTrue(catalog)

    def test_bundle_reconstructs_current_dns_state_from_diff(self):
        bundle, _ = build_evidence_bundle(self.incident)
        self.assertEqual(bundle["previous_state"]["records"][0]["answer"], "203.0.113.10")
        self.assertEqual(bundle["current_state"]["records"][0]["answer"], "198.51.100.20")

    def test_catalog_has_deterministic_dns_and_health_facts(self):
        _, catalog = build_evidence_bundle(self.incident)
        ids = {item["id"] for item in catalog}
        self.assertIn("DNS-001", ids)
        self.assertIn("HEALTH-DNS", ids)
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
        explanation, _ = generate_incident_explanation(
            self.incident,
            explainer=UnavailableExplainer(),
        )
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
        self.assertFalse(payload["safety"]["aiCanMutateDns"])
        self.assertTrue(payload["safety"]["humanApprovalStillRequired"])
        self.assertTrue(payload["evidence"])

    def test_get_before_generation_exposes_read_only_input_contract(self):
        response = self.client.get(f"/api/ai/incidents/{self.incident.id}/explanation/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()["analysis"]
        self.assertEqual(payload["status"], "NOT_GENERATED")
        self.assertEqual(
            set(payload["inputContract"]),
            {
                "previous_state",
                "current_state",
                "dns_diff",
                "health_checks",
                "risk_score",
                "timestamps",
            },
        )

    def test_post_generated_explanation_returns_resolved_deterministic_evidence(self):
        fake = FakeExplainer()
        with patch("core.ai.provider_from_settings", return_value=fake):
            with override_settings(AI_PROVIDER="fake", AI_MODEL="fake-model"):
                response = self.client.post(f"/api/ai/incidents/{self.incident.id}/explanation/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()["analysis"]
        self.assertEqual(payload["status"], "GENERATED")
        self.assertEqual(payload["probableCause"], VALID_ANALYSIS["probable_cause"])
        self.assertEqual([item["id"] for item in payload["evidence"]], VALID_ANALYSIS["evidence_refs"])
        self.assertEqual(payload["label"], "Evidence-based AI analysis")

    def test_get_after_generation_returns_cached_explanation(self):
        fake = FakeExplainer()
        generate_incident_explanation(self.incident, explainer=fake)
        response = self.client.get(f"/api/ai/incidents/{self.incident.id}/explanation/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["analysis"]["cached"])

    def test_missing_incident_returns_404(self):
        response = self.client.get("/api/ai/incidents/999999/explanation/")
        self.assertEqual(response.status_code, 404)
