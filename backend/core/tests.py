import io
import json
from unittest.mock import patch
from urllib import error

from django.test import SimpleTestCase, override_settings

from .namecom import NameComAPIError, NameComClient


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
)
class NameComClientTests(SimpleTestCase):
    def test_sandbox_username_gets_test_suffix(self):
        client = NameComClient()
        self.assertEqual(client.username, "domaintwin-test")
        self.assertEqual(client.base_url, "https://api.dev.name.com")

    @patch("core.namecom.request.urlopen")
    def test_list_domains_uses_core_endpoint(self, urlopen):
        urlopen.return_value = FakeResponse({"domains": [{"domainName": "example.test"}]})

        result = NameComClient().list_domains()

        self.assertEqual(result["domains"][0]["domainName"], "example.test")
        request_object = urlopen.call_args.args[0]
        self.assertEqual(request_object.full_url, "https://api.dev.name.com/core/v1/domains")
        self.assertEqual(request_object.get_method(), "GET")

    def test_mutations_are_blocked_by_default(self):
        client = NameComClient()

        with self.assertRaises(NameComAPIError) as context:
            client.create_record(
                "example.test",
                {"type": "A", "host": "demo", "answer": "203.0.113.10", "ttl": 300},
            )

        self.assertEqual(context.exception.status_code, 403)

    @patch("core.namecom.request.urlopen")
    @override_settings(NAMECOM_ALLOW_MUTATIONS=True)
    def test_create_record_can_run_when_explicitly_enabled(self, urlopen):
        urlopen.return_value = FakeResponse(
            {"id": 7, "type": "A", "host": "demo", "answer": "203.0.113.10", "ttl": 300}
        )

        result = NameComClient().create_record(
            "example.test",
            {"type": "A", "host": "demo", "answer": "203.0.113.10", "ttl": 300},
        )

        self.assertEqual(result["id"], 7)
        request_object = urlopen.call_args.args[0]
        self.assertEqual(request_object.get_method(), "POST")

    @patch("core.namecom.request.urlopen")
    def test_http_429_is_marked_retryable(self, urlopen):
        urlopen.side_effect = error.HTTPError(
            url="https://api.dev.name.com/core/v1/domains",
            code=429,
            msg="Too Many Requests",
            hdrs={},
            fp=io.BytesIO(b'{"message":"Rate limited"}'),
        )

        with self.assertRaises(NameComAPIError) as context:
            NameComClient().list_domains()

        self.assertTrue(context.exception.retryable)
        self.assertEqual(context.exception.status_code, 429)


@override_settings(
    NAMECOM_ENVIRONMENT="production",
    NAMECOM_USERNAME="domaintwin",
    NAMECOM_API_TOKEN="production-secret",
    NAMECOM_TIMEOUT_SECONDS=3,
    NAMECOM_ALLOW_MUTATIONS=True,
    NAMECOM_ALLOW_PRODUCTION_MUTATIONS=False,
)
class ProductionSafetyTests(SimpleTestCase):
    def test_production_mutation_requires_second_opt_in(self):
        with self.assertRaises(NameComAPIError) as context:
            NameComClient().delete_record("example.com", 9)

        self.assertEqual(context.exception.status_code, 403)
        self.assertIn("Production", context.exception.message)
