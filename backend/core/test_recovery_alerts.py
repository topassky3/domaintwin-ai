from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from .models import Incident, ManagedDomain, Membership, Organization, RecoveryPlan
from .tenant import ACTIVE_ORGANIZATION_SESSION_KEY
from .twin import create_snapshot


@override_settings(DOMAIN_TWIN_TESTING=False)
class RecoveryAlertSecurityTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="p6-admin", password="pw")
        self.org_a = Organization.objects.create(name="P6 Tenant A", slug="p6-a")
        self.org_b = Organization.objects.create(name="P6 Tenant B", slug="p6-b")
        Membership.objects.create(
            organization=self.org_a,
            user=self.user,
            role=Membership.Role.ADMIN,
        )
        Membership.objects.create(
            organization=self.org_b,
            user=self.user,
            role=Membership.Role.ADMIN,
        )
        ManagedDomain.objects.create(organization=self.org_a, name="a.example")
        ManagedDomain.objects.create(organization=self.org_a, name="a2.example")
        ManagedDomain.objects.create(organization=self.org_b, name="b.example")

        self.snapshot_a = create_snapshot(
            "a.example",
            [{"type": "A", "host": "@", "answer": "203.0.113.10", "ttl": 300}],
        )
        self.snapshot_a2 = create_snapshot(
            "a2.example",
            [{"type": "A", "host": "@", "answer": "203.0.113.20", "ttl": 300}],
        )
        self.snapshot_b = create_snapshot(
            "b.example",
            [{"type": "A", "host": "@", "answer": "203.0.113.30", "ttl": 300}],
        )

        self.incident_a = self._incident(
            domain="a.example",
            snapshot=self.snapshot_a,
            score=92,
            severity="CRITICAL",
            fingerprint="a" * 64,
        )
        self.incident_b = self._incident(
            domain="b.example",
            snapshot=self.snapshot_b,
            score=75,
            severity="HIGH",
            fingerprint="b" * 64,
        )

        self.client.force_login(self.user)
        self._select(self.org_a)

    def _select(self, organization):
        session = self.client.session
        session[ACTIVE_ORGANIZATION_SESSION_KEY] = str(organization.id)
        session.save()

    def _incident(self, *, domain, snapshot, score, severity, fingerprint):
        return Incident.objects.create(
            domain_name=domain,
            baseline_snapshot=snapshot,
            score=score,
            severity=severity,
            factors=[{"ruleId": "DNS_DRIFT", "points": score, "reason": "DNS drift"}],
            evidence={"domainName": domain},
            evidence_fingerprint=fingerprint,
        )

    def test_alerts_are_tenant_scoped_and_non_disclosing(self):
        response = self.client.get("/api/alerts/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["activeCount"], 1)
        self.assertEqual(payload["alerts"][0]["incidentId"], self.incident_a.id)
        self.assertEqual(payload["alerts"][0]["domainName"], "a.example")
        self.assertNotIn("b.example", response.content.decode("utf-8"))

        self._select(self.org_b)
        switched = self.client.get("/api/alerts/").json()
        self.assertEqual(switched["activeCount"], 1)
        self.assertEqual(switched["alerts"][0]["incidentId"], self.incident_b.id)
        self.assertEqual(switched["alerts"][0]["domainName"], "b.example")

    def test_resolved_incidents_are_not_active_alerts(self):
        self.incident_a.status = Incident.Status.RESOLVED
        self.incident_a.save(update_fields=["status", "resolved_at", "last_seen_at"])
        payload = self.client.get("/api/alerts/").json()
        self.assertEqual(payload["activeCount"], 0)
        self.assertEqual(payload["alerts"], [])
        self.assertIsNone(payload["highestSeverity"])

    def test_corrupted_evidence_chain_is_excluded(self):
        self.incident_a.baseline_snapshot = self.snapshot_a2
        self.incident_a.save(update_fields=["baseline_snapshot", "last_seen_at"])
        payload = self.client.get("/api/alerts/").json()
        self.assertEqual(payload["activeCount"], 0)
        self.assertEqual(payload["alerts"], [])

    def test_alert_includes_only_consistent_latest_recovery_plan(self):
        older = RecoveryPlan.objects.create(
            domain_name="a.example",
            baseline_snapshot=self.snapshot_a,
            incident=self.incident_a,
            status=RecoveryPlan.Status.PREVIEW,
            live_fingerprint_before="1" * 64,
            target_fingerprint="2" * 64,
            plan_fingerprint="3" * 64,
            operations=[{"action": "UPDATE"}],
        )
        newer = RecoveryPlan.objects.create(
            domain_name="a.example",
            baseline_snapshot=self.snapshot_a,
            incident=self.incident_a,
            status=RecoveryPlan.Status.APPROVED,
            live_fingerprint_before="4" * 64,
            target_fingerprint="5" * 64,
            plan_fingerprint="6" * 64,
            operations=[{"action": "UPDATE"}, {"action": "DELETE"}],
        )
        RecoveryPlan.objects.create(
            domain_name="a2.example",
            baseline_snapshot=self.snapshot_a2,
            incident=self.incident_a,
            status=RecoveryPlan.Status.FAILED,
            live_fingerprint_before="7" * 64,
            target_fingerprint="8" * 64,
            plan_fingerprint="9" * 64,
            operations=[{"action": "DELETE"}],
        )

        alert = self.client.get("/api/alerts/").json()["alerts"][0]
        self.assertNotEqual(alert["recoveryPlan"]["id"], older.id)
        self.assertEqual(alert["recoveryPlan"]["id"], newer.id)
        self.assertEqual(alert["recoveryPlan"]["status"], "APPROVED")
        self.assertEqual(alert["recoveryPlan"]["operationCount"], 2)

    def test_alert_read_never_crosses_provider_boundary(self):
        with patch("core.namecom.NameComClient") as client_cls, patch("core.views._client") as client_factory:
            response = self.client.get("/api/alerts/")
        self.assertEqual(response.status_code, 200)
        client_cls.assert_not_called()
        client_factory.assert_not_called()
