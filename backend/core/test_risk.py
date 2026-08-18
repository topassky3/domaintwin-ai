from copy import deepcopy
from unittest.mock import Mock, patch

from django.test import TestCase

from .risk import evaluate_risk, severity_for_score
from .twin import create_snapshot, mark_known_good


class RiskEngineTests(TestCase):
    def test_txt_change_is_low_risk(self):
        diff = {
            "changes": [
                {
                    "state": "REMOVED",
                    "before": {
                        "type": "TXT",
                        "host": "verify",
                        "answer": "baseline",
                        "ttl": 300,
                        "priority": 0,
                    },
                    "after": None,
                }
            ]
        }

        result = evaluate_risk(diff)

        self.assertEqual(result["score"], 5)
        self.assertEqual(result["severity"], "LOW")
        self.assertEqual(result["factorCount"], 1)
        self.assertEqual(result["factors"][0]["ruleId"], "TXT_CHANGED")

    def test_representative_high_risk_case(self):
        diff = {
            "changes": [
                {
                    "state": "REMOVED",
                    "before": {
                        "type": "MX",
                        "host": "@",
                        "answer": "mail.example.test",
                        "ttl": 300,
                        "priority": 10,
                    },
                    "after": None,
                },
                {
                    "state": "MODIFIED",
                    "before": {
                        "type": "NS",
                        "host": "@",
                        "answer": "ns1.old.test",
                        "ttl": 300,
                        "priority": 0,
                    },
                    "after": {
                        "type": "NS",
                        "host": "@",
                        "answer": "ns1.new.test",
                        "ttl": 300,
                        "priority": 0,
                    },
                },
            ]
        }

        result = evaluate_risk(diff)

        self.assertEqual(result["score"], 65)
        self.assertEqual(result["severity"], "HIGH")
        self.assertEqual(
            {factor["ruleId"] for factor in result["factors"]},
            {"MX_REMOVED", "NS_MODIFIED"},
        )

    def test_critical_score_is_capped_at_100(self):
        diff = {
            "changes": [
                {
                    "state": "MODIFIED",
                    "before": {
                        "type": "A",
                        "host": "@",
                        "answer": "203.0.113.10",
                        "ttl": 300,
                        "priority": 0,
                    },
                    "after": {
                        "type": "A",
                        "host": "@",
                        "answer": "203.0.113.99",
                        "ttl": 300,
                        "priority": 0,
                    },
                },
                {
                    "state": "REMOVED",
                    "before": {
                        "type": "MX",
                        "host": "@",
                        "answer": "mail.example.test",
                        "ttl": 300,
                        "priority": 10,
                    },
                    "after": None,
                },
                {
                    "state": "MODIFIED",
                    "before": {
                        "type": "NS",
                        "host": "@",
                        "answer": "ns1.old.test",
                        "ttl": 300,
                        "priority": 0,
                    },
                    "after": {
                        "type": "NS",
                        "host": "@",
                        "answer": "ns1.new.test",
                        "ttl": 300,
                        "priority": 0,
                    },
                },
            ]
        }

        result = evaluate_risk(diff, http_health_failed=True)

        self.assertEqual(result["rawScore"], 125)
        self.assertEqual(result["score"], 100)
        self.assertTrue(result["capped"])
        self.assertEqual(result["severity"], "CRITICAL")

    def test_same_evidence_always_produces_same_result(self):
        changes = [
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
                    "answer": "203.0.113.20",
                    "ttl": 300,
                    "priority": 0,
                },
            },
            {
                "state": "ADDED",
                "before": None,
                "after": {
                    "type": "TXT",
                    "host": "verify",
                    "answer": "new",
                    "ttl": 300,
                    "priority": 0,
                },
            },
        ]
        first = evaluate_risk({"changes": deepcopy(changes)}, unknown_destination=True)
        second = evaluate_risk(
            {"changes": list(reversed(deepcopy(changes)))},
            unknown_destination=True,
        )

        self.assertEqual(first, second)

    def test_severity_boundaries(self):
        self.assertEqual(severity_for_score(0), "LOW")
        self.assertEqual(severity_for_score(24), "LOW")
        self.assertEqual(severity_for_score(25), "MEDIUM")
        self.assertEqual(severity_for_score(49), "MEDIUM")
        self.assertEqual(severity_for_score(50), "HIGH")
        self.assertEqual(severity_for_score(74), "HIGH")
        self.assertEqual(severity_for_score(75), "CRITICAL")
        self.assertEqual(severity_for_score(100), "CRITICAL")


class RiskApiTests(TestCase):
    domain = "domaintwin.test"

    @patch("core.risk_views.NameComClient")
    def test_live_risk_uses_known_good_diff_and_exposes_factors(self, client_cls):
        baseline = create_snapshot(
            self.domain,
            [
                {
                    "type": "TXT",
                    "host": "verify",
                    "answer": "baseline",
                    "ttl": 300,
                }
            ],
        )
        mark_known_good(baseline)

        client = Mock()
        client.list_records.return_value = {"records": []}
        client_cls.return_value = client

        response = self.client.get(f"/api/risk/domains/{self.domain}/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["driftDetected"])
        self.assertEqual(payload["diffSummary"]["REMOVED"], 1)
        self.assertEqual(payload["risk"]["score"], 5)
        self.assertEqual(payload["risk"]["severity"], "LOW")
        self.assertEqual(payload["risk"]["factors"][0]["ruleId"], "TXT_CHANGED")
        self.assertEqual(payload["risk"]["factors"][0]["before"]["answer"], "baseline")

    @patch("core.risk_views.NameComClient")
    def test_context_signals_are_explicit_and_deterministic(self, client_cls):
        baseline = create_snapshot(self.domain, [])
        mark_known_good(baseline)

        client = Mock()
        client.list_records.return_value = {"records": []}
        client_cls.return_value = client

        response = self.client.get(
            f"/api/risk/domains/{self.domain}/?http_health_failed=1&unknown_destination=true"
        )

        self.assertEqual(response.status_code, 200)
        risk = response.json()["risk"]
        self.assertEqual(risk["score"], 45)
        self.assertEqual(risk["severity"], "MEDIUM")
        self.assertEqual(risk["context"]["httpHealthFailed"], True)
        self.assertEqual(risk["context"]["unknownDestination"], True)

    def test_invalid_boolean_context_is_rejected(self):
        baseline = create_snapshot(self.domain, [])
        mark_known_good(baseline)

        response = self.client.get(
            f"/api/risk/domains/{self.domain}/?http_health_failed=maybe"
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("http_health_failed", response.json()["error"]["message"])
