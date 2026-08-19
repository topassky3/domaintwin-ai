import json
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings

from .emergency import (
    EmergencyDomainUnsupported,
    apply_emergency_plan,
    approve_emergency_plan,
    create_emergency_plan,
)
from .models import DomainSnapshot, EmergencyDomainPlan, KnownGoodSnapshot
from .namecom import NameComAPIError, NameComClient
from .twin import normalize_records, snapshot_fingerprint


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


@override_settings(
    NAMECOM_ENVIRONMENT="sandbox",
    NAMECOM_USERNAME="domaintwin",
    NAMECOM_API_TOKEN="secret-token",
    NAMECOM_TIMEOUT_SECONDS=3,
    NAMECOM_ALLOW_MUTATIONS=False,
    NAMECOM_ALLOW_PRODUCTION_MUTATIONS=False,
    NAMECOM_ALLOW_DOMAIN_REGISTRATION=False,
)
class NameComEmergencyClientTests(SimpleTestCase):
    @patch("core.namecom.request.urlopen")
    def test_search_uses_literal_colon_core_endpoint(self, urlopen):
        urlopen.return_value = FakeResponse({"results": []})

        NameComClient().search_domains(keyword="rescue", tld_filter=["com"])

        request_object = urlopen.call_args.args[0]
        self.assertEqual(request_object.full_url, "https://api.dev.name.com/core/v1/domains:search")
        self.assertNotIn("%3A", request_object.full_url)
        self.assertEqual(json.loads(request_object.data)["purchaseType"], "registration")

    @patch("core.namecom.request.urlopen")
    def test_check_availability_uses_registration_inventory(self, urlopen):
        urlopen.return_value = FakeResponse({"results": []})

        NameComClient().check_availability(["rescue-example.com"])

        request_object = urlopen.call_args.args[0]
        self.assertEqual(
            request_object.full_url,
            "https://api.dev.name.com/core/v1/domains:checkAvailability",
        )
        payload = json.loads(request_object.data)
        self.assertEqual(payload["domainNames"], ["rescue-example.com"])
        self.assertEqual(payload["purchaseType"], "registration")

    def test_registration_requires_second_sandbox_opt_in(self):
        with self.assertRaises(NameComAPIError) as context:
            NameComClient().create_domain(
                {"domain": {"domainName": "rescue-example.com"}},
                idempotency_key="test-key",
            )
        self.assertEqual(context.exception.status_code, 403)
        self.assertIn("mutations are disabled", context.exception.message)

    @override_settings(
        NAMECOM_ENVIRONMENT="production",
        NAMECOM_ALLOW_MUTATIONS=True,
        NAMECOM_ALLOW_PRODUCTION_MUTATIONS=True,
        NAMECOM_ALLOW_DOMAIN_REGISTRATION=True,
    )
    def test_gate8_registration_is_never_allowed_in_production(self):
        with self.assertRaises(NameComAPIError) as context:
            NameComClient().create_domain(
                {"domain": {"domainName": "rescue-example.com"}},
                idempotency_key="test-key",
            )
        self.assertEqual(context.exception.status_code, 403)
        self.assertIn("sandbox-only", context.exception.message)

    @patch("core.namecom.request.urlopen")
    @override_settings(NAMECOM_ALLOW_MUTATIONS=True, NAMECOM_ALLOW_DOMAIN_REGISTRATION=True)
    def test_sandbox_registration_sends_idempotency_key(self, urlopen):
        urlopen.return_value = FakeResponse(
            {
                "domain": {"domainName": "rescue-example.com"},
                "order": 7,
                "totalPaid": 0,
            }
        )

        NameComClient().create_domain(
            {"domain": {"domainName": "rescue-example.com"}},
            idempotency_key="gate8-idempotency-key",
        )

        request_object = urlopen.call_args.args[0]
        self.assertEqual(request_object.get_method(), "POST")
        self.assertEqual(request_object.full_url, "https://api.dev.name.com/core/v1/domains")
        self.assertEqual(request_object.get_header("X-idempotency-key"), "gate8-idempotency-key")


class FakeEmergencyClient:
    environment = "sandbox"

    def __init__(self, target="rescue-example.com", *, premium=False):
        self.target = target
        self.premium = premium
        self.records = []
        self.registration_keys = []
        self.next_id = 100

    def check_availability(self, domain_names):
        return {
            "results": [
                {
                    "domainName": self.target,
                    "purchasable": True,
                    "sld": self.target.split(".")[0],
                    "tld": self.target.rsplit(".", 1)[-1],
                    "premium": self.premium,
                    "purchasePrice": 12.34,
                    "renewalPrice": 18.99,
                    "purchaseType": "registration",
                }
            ]
        }

    def create_domain(self, payload, *, idempotency_key):
        self.registration_keys.append(idempotency_key)
        return {
            "domain": {
                "domainName": payload["domain"]["domainName"],
                "createDate": "2026-08-19T12:00:00Z",
                "expireDate": "2027-08-19T12:00:00Z",
                "locked": True,
                "privacyEnabled": True,
            },
            "order": 88,
            "totalPaid": 0,
        }

    def list_records(self, domain_name):
        return {"records": list(self.records)}

    def create_record(self, domain_name, payload):
        self.next_id += 1
        record = {**payload, "id": self.next_id}
        self.records.append(record)
        return record


class RetryRegistrationClient(FakeEmergencyClient):
    def __init__(self, target="rescue-example.com"):
        super().__init__(target)
        self.registration_attempts = 0
        self.availability_checks = 0

    def check_availability(self, domain_names):
        self.availability_checks += 1
        return super().check_availability(domain_names)

    def create_domain(self, payload, *, idempotency_key):
        self.registration_attempts += 1
        self.registration_keys.append(idempotency_key)
        if self.registration_attempts == 1:
            raise NameComAPIError(
                status_code=504,
                message="Simulated provider timeout after request submission.",
                retryable=True,
            )
        return {
            "domain": {"domainName": payload["domain"]["domainName"]},
            "order": 99,
            "totalPaid": 0,
        }


class EmergencyDomainPlanTests(TestCase):
    source = "primary-example.com"
    target = "rescue-example.com"

    def setUp(self):
        records = normalize_records(
            [{"type": "A", "host": "www", "answer": "203.0.113.10", "ttl": 300}]
        )
        snapshot = DomainSnapshot.objects.create(
            domain_name=self.source,
            version=1,
            records=records,
            fingerprint=snapshot_fingerprint(records),
        )
        KnownGoodSnapshot.objects.create(domain_name=self.source, snapshot=snapshot)

    def test_preview_is_read_only_and_audited(self):
        client = FakeEmergencyClient(self.target)

        plan, created = create_emergency_plan(
            source_domain=self.source,
            target_domain=self.target,
            client=client,
        )

        self.assertTrue(created)
        self.assertEqual(plan.status, EmergencyDomainPlan.Status.PREVIEW)
        self.assertEqual(len(plan.operations), 1)
        self.assertEqual(plan.operations[0]["action"], "CREATE")
        self.assertEqual(plan.audit_events.get(sequence=1).event_type, "PLAN_CREATED")
        self.assertEqual(client.registration_keys, [])

    def test_premium_candidate_is_rejected_before_plan_creation(self):
        with self.assertRaises(EmergencyDomainUnsupported):
            create_emergency_plan(
                source_domain=self.source,
                target_domain=self.target,
                client=FakeEmergencyClient(self.target, premium=True),
            )
        self.assertEqual(EmergencyDomainPlan.objects.count(), 0)

    def test_approval_is_explicit_state_transition(self):
        plan, _ = create_emergency_plan(
            source_domain=self.source,
            target_domain=self.target,
            client=FakeEmergencyClient(self.target),
        )

        approve_emergency_plan(plan)

        plan.refresh_from_db()
        self.assertEqual(plan.status, EmergencyDomainPlan.Status.APPROVED)
        self.assertEqual(plan.audit_events.get(sequence=2).event_type, "PLAN_APPROVED")

    def test_apply_registers_clones_and_verifies_exact_fingerprint(self):
        client = FakeEmergencyClient(self.target)
        plan, _ = create_emergency_plan(
            source_domain=self.source,
            target_domain=self.target,
            client=client,
        )
        approve_emergency_plan(plan)

        result = apply_emergency_plan(plan, client=client)

        self.assertEqual(result.status, EmergencyDomainPlan.Status.READY)
        self.assertTrue(result.verification["matched"])
        self.assertEqual(result.actual_fingerprint, result.expected_fingerprint)
        self.assertEqual(result.registration["domainName"], self.target)
        self.assertEqual(client.registration_keys, [plan.idempotency_key])
        self.assertEqual(result.operation_results[0]["status"], "SUCCEEDED")
        events = list(result.audit_events.values_list("event_type", flat=True))
        self.assertEqual(
            events,
            [
                "PLAN_CREATED",
                "PLAN_APPROVED",
                "REGISTRATION_STARTED",
                "DOMAIN_REGISTERED",
                "CLONE_STARTED",
                "DNS_RECORD_CLONED",
                "CLONE_VERIFIED",
                "EMERGENCY_DOMAIN_READY",
            ],
        )

    def test_apply_can_resume_registration_with_same_idempotency_key_after_timeout(self):
        client = RetryRegistrationClient(self.target)
        plan, _ = create_emergency_plan(
            source_domain=self.source,
            target_domain=self.target,
            client=client,
        )
        approve_emergency_plan(plan)
        checks_before_apply = client.availability_checks

        with self.assertRaises(NameComAPIError):
            apply_emergency_plan(plan, client=client)

        plan.refresh_from_db()
        self.assertEqual(plan.status, EmergencyDomainPlan.Status.APPLYING)
        self.assertEqual(plan.registration, {})

        result = apply_emergency_plan(plan, client=client)

        self.assertEqual(result.status, EmergencyDomainPlan.Status.READY)
        self.assertEqual(client.registration_keys, [plan.idempotency_key, plan.idempotency_key])
        self.assertEqual(client.availability_checks, checks_before_apply + 1)
        events = list(result.audit_events.values_list("event_type", flat=True))
        self.assertIn("APPLY_RESUMED", events)
        self.assertIn("REGISTRATION_RETRY", events)
        self.assertEqual(events[-1], "EMERGENCY_DOMAIN_READY")
