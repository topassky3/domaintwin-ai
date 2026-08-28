from __future__ import annotations

from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from .models import (
    DomainSnapshot,
    HealthObservation,
    KnownGoodSnapshot,
    ManagedDomain,
    Membership,
    Organization,
    ProviderConnection,
)
from .provider_middleware import requires_namecom_provider
from .tenant import ACTIVE_ORGANIZATION_SESSION_KEY


@override_settings(
    DOMAIN_TWIN_TESTING=False,
    NAMECOM_ENVIRONMENT="sandbox",
    NAMECOM_USERNAME="p7-demo-user",
    NAMECOM_API_TOKEN="P7_SECRET_MUST_NOT_LEAK",
    NAMECOM_ALLOW_MUTATIONS=True,
    NAMECOM_ALLOW_PRODUCTION_MUTATIONS=False,
    NAMECOM_ALLOW_DOMAIN_REGISTRATION=False,
    DOMAIN_MONITOR_INTERVAL_SECONDS=60,
)
class DemoHardeningTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="p7-admin", password="pw")
        self.org_a = Organization.objects.create(name="P7 Tenant A", slug="p7-a")
        self.org_b = Organization.objects.create(name="P7 Tenant B", slug="p7-b")
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
        self.client.force_login(self.user)
        self._select(self.org_a)

    def _select(self, organization):
        session = self.client.session
        session[ACTIVE_ORGANIZATION_SESSION_KEY] = str(organization.id)
        session.save()

    def _make_ready(self, organization, domain_name: str):
        ManagedDomain.objects.create(organization=organization, name=domain_name)
        snapshot = DomainSnapshot.objects.create(
            domain_name=domain_name,
            version=1,
            records=[],
            fingerprint="a" * 64,
        )
        KnownGoodSnapshot.objects.create(domain_name=domain_name, snapshot=snapshot)
        HealthObservation.objects.create(
            domain_name=domain_name,
            dns_resolution={"ok": True},
            http={"ok": True, "statusCode": 200},
            https={"ok": True, "statusCode": 200},
            availability_ok=True,
        )
        return snapshot

    def test_ready_preflight_exposes_no_secret_values(self):
        self._make_ready(self.org_a, "ready-a.example")

        response = self.client.get("/api/demo/readiness/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "READY")
        self.assertEqual(payload["blockerCount"], 0)
        self.assertEqual(payload["primaryDomain"], "ready-a.example")
        self.assertEqual(payload["warningCount"], 1)
        body = response.content.decode("utf-8")
        self.assertNotIn("P7_SECRET_MUST_NOT_LEAK", body)
        self.assertNotIn("p7-demo-user", body)

    def test_preflight_is_database_only_and_reports_missing_provider_binding(self):
        self._make_ready(self.org_a, "binding-a.example")
        ProviderConnection.objects.filter(organization=self.org_a).delete()

        self.assertFalse(requires_namecom_provider("/api/demo/readiness/", "GET"))
        response = self.client.get("/api/demo/readiness/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "BLOCKED")
        provider_check = next(
            row for row in response.json()["checks"] if row["id"] == "provider_binding"
        )
        self.assertEqual(provider_check["status"], "FAIL")

    def test_missing_domain_and_baseline_block_demo_without_crashing(self):
        response = self.client.get("/api/demo/readiness/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "BLOCKED")
        self.assertIsNone(payload["primaryDomain"])
        self.assertEqual(payload["managedDomainCount"], 0)
        self.assertGreaterEqual(payload["blockerCount"], 2)

    def test_corrupted_known_good_chain_is_not_counted_as_ready(self):
        domain_name = "corrupt-a.example"
        ManagedDomain.objects.create(organization=self.org_a, name=domain_name)
        wrong_snapshot = DomainSnapshot.objects.create(
            domain_name="other-a.example",
            version=1,
            records=[],
            fingerprint="b" * 64,
        )
        KnownGoodSnapshot.objects.create(domain_name=domain_name, snapshot=wrong_snapshot)

        response = self.client.get("/api/demo/readiness/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["knownGoodDomainCount"], 0)
        baseline_check = next(
            row for row in payload["checks"] if row["id"] == "known_good_baseline"
        )
        self.assertEqual(baseline_check["status"], "FAIL")

    def test_preflight_never_falls_back_to_another_tenant(self):
        self._make_ready(self.org_b, "ready-b.example")

        response_a = self.client.get("/api/demo/readiness/")
        self.assertEqual(response_a.status_code, 200)
        self.assertEqual(response_a.json()["organization"]["slug"], "p7-a")
        self.assertEqual(response_a.json()["managedDomainCount"], 0)
        self.assertEqual(response_a.json()["status"], "BLOCKED")

        self._select(self.org_b)
        response_b = self.client.get("/api/demo/readiness/")
        self.assertEqual(response_b.status_code, 200)
        self.assertEqual(response_b.json()["organization"]["slug"], "p7-b")
        self.assertEqual(response_b.json()["primaryDomain"], "ready-b.example")
        self.assertEqual(response_b.json()["status"], "READY")

    def test_management_command_is_green_only_when_required_checks_pass(self):
        self._make_ready(self.org_a, "command-a.example")
        output = StringIO()

        call_command("demo_readiness", "--organization", "p7-a", stdout=output)
        self.assertIn("STATUS=READY", output.getvalue())

        KnownGoodSnapshot.objects.filter(domain_name="command-a.example").delete()
        with self.assertRaises(CommandError):
            call_command(
                "demo_readiness",
                "--organization",
                "p7-a",
                stdout=StringIO(),
                stderr=StringIO(),
            )
