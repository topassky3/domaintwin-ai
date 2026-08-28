from __future__ import annotations

import io
import json
from unittest.mock import Mock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from .models import ManagedDomain, Organization, ProviderConnection
from .monitoring import evaluate_domain_state, run_monitoring_cycle
from .twin import create_snapshot, mark_known_good


def healthy_result(domain: str) -> dict:
    return {
        "domainName": domain,
        "dnsResolution": {"ok": True, "addresses": ["93.184.216.34"], "error": None},
        "http": {
            "url": f"http://{domain}/",
            "ok": True,
            "statusCode": 200,
            "latencyMs": 1.0,
            "finalUrl": f"http://{domain}/",
            "error": None,
        },
        "https": {
            "url": f"https://{domain}/",
            "ok": True,
            "statusCode": 200,
            "latencyMs": 1.0,
            "finalUrl": f"https://{domain}/",
            "error": None,
        },
        "availabilityOk": True,
        "availabilityFailed": False,
    }


class MonitoringLiteTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="P5 Tenant", slug="p5-tenant")
        self.domain = ManagedDomain.objects.create(
            organization=self.organization,
            name="a.example",
        )
        self.records = [
            {"type": "A", "host": "@", "answer": "203.0.113.10", "ttl": 300}
        ]

    def _baseline(self, domain_name: str, records=None):
        snapshot = create_snapshot(domain_name, records or self.records)
        mark_known_good(snapshot)
        return snapshot

    def test_reusable_evaluator_preserves_deterministic_healthy_pipeline(self):
        baseline = self._baseline(self.domain.name)
        provider = Mock()
        provider.list_records.return_value = {"records": self.records}

        result = evaluate_domain_state(
            self.domain.name,
            client=provider,
            health_checker=healthy_result,
        )

        self.assertEqual(result["state"], "HEALTHY")
        self.assertEqual(result["baseline"].id, baseline.id)
        self.assertFalse(result["driftDetected"])
        self.assertFalse(result["incidentCreated"])
        self.assertIsNone(result["incident"])
        provider.list_records.assert_called_once_with(self.domain.name)

    def test_cycle_checks_active_domain_and_skips_missing_baseline_before_provider(self):
        self._baseline(self.domain.name)
        ManagedDomain.objects.create(
            organization=self.organization,
            name="b.example",
        )
        inactive = ManagedDomain.objects.create(
            organization=self.organization,
            name="c.example",
        )
        inactive.is_active = False
        inactive.save(update_fields=["is_active", "updated_at"])

        provider = Mock()
        provider.list_records.return_value = {"records": self.records}
        factory = Mock(return_value=provider)

        summary = run_monitoring_cycle(
            client_factory=factory,
            health_checker=healthy_result,
        )

        self.assertEqual(summary["checked"], 1)
        self.assertEqual(summary["healthy"], 1)
        self.assertEqual(summary["skipped"], 1)
        self.assertEqual(summary["failed"], 0)
        self.assertEqual(
            next(row for row in summary["results"] if row["domainName"] == "b.example")["reason"],
            "KNOWN_GOOD_BASELINE_REQUIRED",
        )
        factory.assert_called_once_with()
        provider.list_records.assert_called_once_with("a.example")

    def test_inactive_provider_binding_skips_before_client_factory(self):
        self._baseline(self.domain.name)
        connection = ProviderConnection.objects.get(
            organization=self.organization,
            provider=ProviderConnection.Provider.NAMECOM,
        )
        connection.is_active = False
        connection.save(update_fields=["is_active", "updated_at"])
        factory = Mock()

        summary = run_monitoring_cycle(
            client_factory=factory,
            health_checker=healthy_result,
        )

        self.assertEqual(summary["checked"], 0)
        self.assertEqual(summary["skipped"], 1)
        self.assertEqual(summary["results"][0]["reason"], "PROVIDER_CONNECTION_REQUIRED")
        factory.assert_not_called()

    def test_one_domain_provider_failure_does_not_stop_other_domains(self):
        self._baseline(self.domain.name)
        second = ManagedDomain.objects.create(
            organization=self.organization,
            name="b.example",
        )
        self._baseline(second.name)

        good = Mock()
        good.list_records.return_value = {"records": self.records}
        bad = Mock()
        bad.list_records.side_effect = RuntimeError("provider unavailable")
        factory = Mock(side_effect=[good, bad])

        summary = run_monitoring_cycle(
            client_factory=factory,
            health_checker=healthy_result,
        )

        self.assertEqual(summary["checked"], 1)
        self.assertEqual(summary["healthy"], 1)
        self.assertEqual(summary["failed"], 1)
        failed = next(row for row in summary["results"] if row["outcome"] == "FAILED")
        self.assertEqual(failed["domainName"], "b.example")
        self.assertEqual(failed["errorType"], "RuntimeError")

    @patch("core.management.commands.monitor_domaintwin.run_monitoring_cycle")
    def test_management_command_runs_one_scheduler_friendly_cycle(self, cycle):
        cycle.return_value = {
            "checked": 1,
            "healthy": 1,
            "degraded": 0,
            "incident": 0,
            "skipped": 0,
            "failed": 0,
            "results": [],
        }
        stdout = io.StringIO()

        call_command("monitor_domaintwin", "--organization", "p5-tenant", stdout=stdout)

        cycle.assert_called_once_with(
            organization_slug="p5-tenant",
            domain_names=None,
        )
        payload = json.loads(stdout.getvalue().strip())
        self.assertEqual(payload["checked"], 1)
        self.assertEqual(payload["healthy"], 1)

    def test_loop_rejects_aggressive_provider_polling(self):
        with self.assertRaises(CommandError):
            call_command("monitor_domaintwin", "--loop", "--interval-seconds", "1")
