from unittest.mock import patch

from django.test import TestCase

from .health import ResolutionResult, UnsafeHealthTarget, check_domain_health, normalize_health_host
from .incidents import monitor_state, unknown_destination_detected
from .models import HealthObservation, Incident, IncidentEvent
from .twin import create_snapshot, diff_records, mark_known_good


def healthy_result(domain="example.com"):
    return {
        "domainName": domain,
        "dnsResolution": {"ok": True, "addresses": ["93.184.216.34"], "error": None},
        "http": {
            "url": f"http://{domain}/",
            "ok": True,
            "statusCode": 200,
            "latencyMs": 12.0,
            "finalUrl": f"http://{domain}/",
            "error": None,
        },
        "https": {
            "url": f"https://{domain}/",
            "ok": True,
            "statusCode": 200,
            "latencyMs": 15.0,
            "finalUrl": f"https://{domain}/",
            "error": None,
        },
        "availabilityOk": True,
        "availabilityFailed": False,
    }


def failed_result(domain="example.com"):
    return {
        "domainName": domain,
        "dnsResolution": {"ok": False, "addresses": [], "error": "DNS resolution failed"},
        "http": {
            "url": f"http://{domain}/",
            "ok": False,
            "statusCode": None,
            "latencyMs": 0.0,
            "finalUrl": None,
            "error": "DNS resolution failed",
        },
        "https": {
            "url": f"https://{domain}/",
            "ok": False,
            "statusCode": None,
            "latencyMs": 0.0,
            "finalUrl": None,
            "error": "DNS resolution failed",
        },
        "availabilityOk": False,
        "availabilityFailed": True,
    }


class HealthProbeTests(TestCase):
    def test_health_target_rejects_urls_localhost_and_direct_ip(self):
        for value in ("http://example.com", "localhost", "127.0.0.1", "example.com/path"):
            with self.subTest(value=value):
                with self.assertRaises(UnsafeHealthTarget):
                    normalize_health_host(value)

    @patch("core.health._probe_url")
    @patch("core.health.resolve_public_host")
    def test_http_or_https_success_means_available(self, resolve_host, probe_url):
        resolve_host.return_value = ResolutionResult(True, ("93.184.216.34",), None)
        probe_url.side_effect = [
            {"ok": False, "statusCode": 500, "latencyMs": 1.0, "finalUrl": "http://example.com/", "error": "HTTP status 500."},
            {"ok": True, "statusCode": 200, "latencyMs": 2.0, "finalUrl": "https://example.com/", "error": None},
        ]
        result = check_domain_health("example.com")
        self.assertTrue(result["availabilityOk"])
        self.assertFalse(result["availabilityFailed"])
        self.assertFalse(result["http"]["ok"])
        self.assertTrue(result["https"]["ok"])

    @patch("core.health.resolve_public_host")
    def test_dns_resolution_failure_records_both_protocols_as_failed(self, resolve_host):
        resolve_host.return_value = ResolutionResult(False, (), "DNS resolution failed")
        result = check_domain_health("example.com")
        self.assertTrue(result["availabilityFailed"])
        self.assertFalse(result["http"]["ok"])
        self.assertFalse(result["https"]["ok"])


class IncidentDecisionTests(TestCase):
    def test_state_machine_healthy_degraded_and_incident(self):
        low_risk = {"score": 5, "factors": [{"ruleId": "TXT_CHANGED"}]}
        dangerous_risk = {"score": 45, "factors": [{"ruleId": "ADDRESS_RECORD_CHANGED"}]}
        self.assertEqual(
            monitor_state(drift_detected=False, availability_failed=False, risk={"score": 0, "factors": []}),
            "HEALTHY",
        )
        self.assertEqual(
            monitor_state(drift_detected=True, availability_failed=False, risk=low_risk),
            "DEGRADED",
        )
        self.assertEqual(
            monitor_state(drift_detected=False, availability_failed=True, risk={"score": 30, "factors": []}),
            "DEGRADED",
        )
        self.assertEqual(
            monitor_state(drift_detected=True, availability_failed=False, risk=dangerous_risk),
            "INCIDENT",
        )
        self.assertEqual(
            monitor_state(drift_detected=True, availability_failed=True, risk=low_risk),
            "INCIDENT",
        )

    def test_unknown_destination_is_derived_from_changed_address(self):
        before = [{"type": "A", "host": "@", "answer": "203.0.113.10", "ttl": 300}]
        after = [{"type": "A", "host": "@", "answer": "198.51.100.20", "ttl": 300}]
        diff = diff_records(before, after)
        self.assertTrue(unknown_destination_detected(before, diff))


class MonitorApiTests(TestCase):
    domain = "example.com"

    def setUp(self):
        self.baseline_records = [
            {"type": "A", "host": "@", "answer": "203.0.113.10", "ttl": 300}
        ]
        self.snapshot = create_snapshot(self.domain, self.baseline_records)
        mark_known_good(self.snapshot)

    @patch("core.monitor_views.check_domain_health")
    @patch("core.monitor_views.NameComClient")
    def test_matching_dns_and_healthy_probe_starts_healthy(self, client_cls, health_check):
        client_cls.return_value.list_records.return_value = {"records": self.baseline_records}
        health_check.return_value = healthy_result(self.domain)

        response = self.client.post(f"/api/monitor/domains/{self.domain}/evaluate/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["state"], "HEALTHY")
        self.assertFalse(payload["driftDetected"])
        self.assertTrue(payload["health"]["availabilityOk"])
        self.assertIsNone(payload["incident"])
        self.assertEqual(HealthObservation.objects.count(), 1)
        self.assertEqual(Incident.objects.count(), 0)

    @patch("core.monitor_views.check_domain_health")
    @patch("core.monitor_views.NameComClient")
    def test_health_failure_is_recorded_independently_without_dns_drift(self, client_cls, health_check):
        client_cls.return_value.list_records.return_value = {"records": self.baseline_records}
        health_check.return_value = failed_result(self.domain)

        response = self.client.post(f"/api/monitor/domains/{self.domain}/evaluate/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["state"], "DEGRADED")
        self.assertFalse(payload["driftDetected"])
        self.assertTrue(payload["health"]["availabilityFailed"])
        self.assertEqual(payload["risk"]["score"], 30)
        self.assertEqual(HealthObservation.objects.count(), 1)
        self.assertEqual(Incident.objects.count(), 0)

    @patch("core.monitor_views.check_domain_health")
    @patch("core.monitor_views.NameComClient")
    def test_dangerous_dns_change_plus_failure_opens_critical_incident(self, client_cls, health_check):
        changed = [{"type": "A", "host": "@", "answer": "198.51.100.20", "ttl": 300}]
        client_cls.return_value.list_records.return_value = {"records": changed}
        health_check.return_value = failed_result(self.domain)

        response = self.client.post(f"/api/monitor/domains/{self.domain}/evaluate/")
        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["state"], "INCIDENT")
        self.assertTrue(payload["driftDetected"])
        self.assertTrue(payload["unknownDestination"])
        self.assertEqual(payload["risk"]["score"], 75)
        self.assertEqual(payload["risk"]["severity"], "CRITICAL")
        self.assertTrue(payload["incidentCreated"])
        self.assertEqual(Incident.objects.count(), 1)
        incident = Incident.objects.get()
        self.assertEqual(incident.status, Incident.Status.OPEN)
        self.assertEqual(incident.score, 75)
        self.assertEqual(
            list(incident.timeline.values_list("event_type", flat=True)),
            ["DNS_EVIDENCE_CAPTURED", "HEALTH_EVIDENCE_CAPTURED", "INCIDENT_OPENED"],
        )

    @patch("core.monitor_views.check_domain_health")
    @patch("core.monitor_views.NameComClient")
    def test_repeated_same_event_reuses_incident_without_duplicate_timeline(self, client_cls, health_check):
        changed = [{"type": "A", "host": "@", "answer": "198.51.100.20", "ttl": 300}]
        client_cls.return_value.list_records.return_value = {"records": changed}
        health_check.return_value = failed_result(self.domain)

        first = self.client.post(f"/api/monitor/domains/{self.domain}/evaluate/")
        second = self.client.post(f"/api/monitor/domains/{self.domain}/evaluate/")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["incident"]["id"], second.json()["incident"]["id"])
        self.assertFalse(second.json()["incidentCreated"])
        self.assertEqual(Incident.objects.count(), 1)
        self.assertEqual(IncidentEvent.objects.count(), 3)
        self.assertEqual(HealthObservation.objects.count(), 2)

    @patch("core.monitor_views.check_domain_health")
    @patch("core.monitor_views.NameComClient")
    def test_new_evidence_updates_same_active_incident(self, client_cls, health_check):
        changed = [{"type": "A", "host": "@", "answer": "198.51.100.20", "ttl": 300}]
        client_cls.return_value.list_records.return_value = {"records": changed}
        health_check.return_value = failed_result(self.domain)
        self.client.post(f"/api/monitor/domains/{self.domain}/evaluate/")

        health_check.return_value = healthy_result(self.domain)
        response = self.client.post(f"/api/monitor/domains/{self.domain}/evaluate/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["state"], "INCIDENT")
        self.assertEqual(Incident.objects.count(), 1)
        self.assertEqual(IncidentEvent.objects.count(), 4)
        self.assertEqual(IncidentEvent.objects.order_by("sequence").last().event_type, "INCIDENT_UPDATED")

    @patch("core.monitor_views.check_domain_health")
    @patch("core.monitor_views.NameComClient")
    def test_restored_dns_and_health_resolves_active_incident(self, client_cls, health_check):
        changed = [{"type": "A", "host": "@", "answer": "198.51.100.20", "ttl": 300}]
        client_cls.return_value.list_records.return_value = {"records": changed}
        health_check.return_value = failed_result(self.domain)
        opened = self.client.post(f"/api/monitor/domains/{self.domain}/evaluate/")
        incident_id = opened.json()["incident"]["id"]

        client_cls.return_value.list_records.return_value = {"records": self.baseline_records}
        health_check.return_value = healthy_result(self.domain)
        restored = self.client.post(f"/api/monitor/domains/{self.domain}/evaluate/")
        self.assertEqual(restored.status_code, 200)
        self.assertEqual(restored.json()["state"], "HEALTHY")
        incident = Incident.objects.get(id=incident_id)
        self.assertEqual(incident.status, Incident.Status.RESOLVED)
        self.assertIsNotNone(incident.resolved_at)
        self.assertEqual(incident.timeline.order_by("sequence").last().event_type, "INCIDENT_RESOLVED")

    def test_health_endpoint_rejects_private_or_direct_ip_target(self):
        response = self.client.get("/api/monitor/domains/127.0.0.1/health/")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["status"], 400)
