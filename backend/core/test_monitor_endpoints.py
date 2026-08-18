from unittest.mock import patch

from django.test import TestCase

from .models import Incident
from .twin import create_snapshot, mark_known_good


class MonitorQueryEndpointTests(TestCase):
    domain = "example.com"

    def setUp(self):
        self.baseline = [
            {"type": "A", "host": "@", "answer": "203.0.113.10", "ttl": 300}
        ]
        snapshot = create_snapshot(self.domain, self.baseline)
        mark_known_good(snapshot)

    @staticmethod
    def failed_health():
        return {
            "domainName": "example.com",
            "dnsResolution": {"ok": False, "addresses": [], "error": "DNS resolution failed"},
            "http": {"url": "http://example.com/", "ok": False, "statusCode": None, "latencyMs": 0.0, "finalUrl": None, "error": "DNS resolution failed"},
            "https": {"url": "https://example.com/", "ok": False, "statusCode": None, "latencyMs": 0.0, "finalUrl": None, "error": "DNS resolution failed"},
            "availabilityOk": False,
            "availabilityFailed": True,
        }

    @patch("core.monitor_views.check_domain_health")
    @patch("core.monitor_views.NameComClient")
    def test_status_list_and_detail_expose_same_incident_and_ordered_timeline(self, client_cls, health_check):
        client_cls.return_value.list_records.return_value = {
            "records": [{"type": "A", "host": "@", "answer": "198.51.100.20", "ttl": 300}]
        }
        health_check.return_value = self.failed_health()

        opened = self.client.post(f"/api/monitor/domains/{self.domain}/evaluate/")
        incident_id = opened.json()["incident"]["id"]

        status = self.client.get(f"/api/monitor/domains/{self.domain}/status/")
        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.json()["state"], "INCIDENT")
        self.assertEqual(status.json()["activeIncident"]["id"], incident_id)

        listing = self.client.get(f"/api/incidents/domains/{self.domain}/")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()["totalCount"], 1)
        self.assertEqual(listing.json()["incidents"][0]["id"], incident_id)

        detail = self.client.get(f"/api/incidents/{incident_id}/")
        self.assertEqual(detail.status_code, 200)
        timeline = detail.json()["incident"]["timeline"]
        self.assertEqual([event["sequence"] for event in timeline], [1, 2, 3])
        self.assertEqual(
            [event["eventType"] for event in timeline],
            ["DNS_EVIDENCE_CAPTURED", "HEALTH_EVIDENCE_CAPTURED", "INCIDENT_OPENED"],
        )
        self.assertEqual(Incident.objects.count(), 1)

    def test_evaluate_without_known_good_returns_json_404(self):
        response = self.client.post("/api/monitor/domains/missing.example/evaluate/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["status"], 404)
