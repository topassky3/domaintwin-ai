from unittest.mock import Mock, patch

from django.test import TestCase

from .models import DomainSnapshot, KnownGoodSnapshot
from .twin import (
    create_snapshot,
    diff_records,
    mark_known_good,
    normalize_record,
    normalize_records,
    snapshot_fingerprint,
)


class NormalizationTests(TestCase):
    def test_record_normalization_is_canonical(self):
        record = normalize_record(
            {
                "type": "a",
                "host": "www.",
                "answer": "203.0.113.10.",
                "ttl": "300",
            }
        )
        self.assertEqual(
            record,
            {
                "type": "A",
                "host": "www",
                "answer": "203.0.113.10",
                "ttl": 300,
                "priority": 0,
            },
        )

    def test_fingerprint_is_stable_regardless_of_input_order(self):
        records_a = [
            {"type": "TXT", "host": "verify", "answer": "ok", "ttl": 300},
            {"type": "A", "host": "@", "answer": "203.0.113.10", "ttl": 300},
        ]
        records_b = list(reversed(records_a))
        normalized_a = normalize_records(records_a)
        normalized_b = normalize_records(records_b)
        self.assertEqual(normalized_a, normalized_b)
        self.assertEqual(snapshot_fingerprint(normalized_a), snapshot_fingerprint(normalized_b))


class DiffEngineTests(TestCase):
    def test_diff_detects_added_removed_modified_and_unchanged(self):
        before = [
            {"type": "A", "host": "@", "answer": "203.0.113.10", "ttl": 300},
            {"type": "MX", "host": "@", "answer": "mail.old.test", "ttl": 300, "priority": 10},
            {"type": "TXT", "host": "verify", "answer": "same", "ttl": 300},
        ]
        after = [
            {"type": "A", "host": "@", "answer": "203.0.113.20", "ttl": 300},
            {"type": "TXT", "host": "verify", "answer": "same", "ttl": 300},
            {"type": "CNAME", "host": "www", "answer": "new.test", "ttl": 300},
        ]

        result = diff_records(before, after)

        self.assertEqual(
            result["summary"],
            {"ADDED": 1, "REMOVED": 1, "MODIFIED": 1, "UNCHANGED": 1},
        )
        modified = next(change for change in result["changes"] if change["state"] == "MODIFIED")
        self.assertEqual(modified["before"]["answer"], "203.0.113.10")
        self.assertEqual(modified["after"]["answer"], "203.0.113.20")


class SnapshotPersistenceTests(TestCase):
    def test_snapshot_versions_and_content_are_immutable(self):
        first = create_snapshot(
            "example.test",
            [{"type": "A", "host": "@", "answer": "203.0.113.10", "ttl": 300}],
        )
        second = create_snapshot(
            "example.test",
            [{"type": "A", "host": "@", "answer": "203.0.113.20", "ttl": 300}],
        )

        self.assertEqual(first.version, 1)
        self.assertEqual(second.version, 2)
        first.refresh_from_db()
        self.assertEqual(first.records[0]["answer"], "203.0.113.10")

        first.fingerprint = "x" * 64
        with self.assertRaisesMessage(ValueError, "immutable"):
            first.save()

    def test_known_good_pointer_can_move_without_mutating_snapshots(self):
        first = create_snapshot("example.test", [])
        second = create_snapshot(
            "example.test",
            [{"type": "TXT", "host": "version", "answer": "2", "ttl": 300}],
        )
        mark_known_good(first)
        marker = mark_known_good(second)

        self.assertEqual(marker.snapshot_id, second.id)
        self.assertEqual(KnownGoodSnapshot.objects.get(domain_name="example.test").snapshot_id, second.id)
        self.assertEqual(DomainSnapshot.objects.count(), 2)


class SnapshotApiTests(TestCase):
    domain = "domaintwin.test"

    @patch("core.twin_views.NameComClient")
    def test_capture_mark_known_good_and_compare_live_dns(self, client_cls):
        client = Mock()
        client.list_records.return_value = {
            "records": [
                {"type": "A", "host": "@", "answer": "203.0.113.10", "ttl": 300}
            ]
        }
        client_cls.return_value = client

        capture = self.client.post(f"/api/twin/domains/{self.domain}/snapshots/")
        self.assertEqual(capture.status_code, 201)
        snapshot_id = capture.json()["snapshot"]["id"]
        self.assertEqual(capture.json()["snapshot"]["version"], 1)

        marked = self.client.post(
            f"/api/twin/domains/{self.domain}/snapshots/{snapshot_id}/known-good/"
        )
        self.assertEqual(marked.status_code, 200)
        self.assertEqual(marked.json()["knownGoodSnapshotId"], snapshot_id)

        client.list_records.return_value = {
            "records": [
                {"type": "A", "host": "@", "answer": "203.0.113.99", "ttl": 300},
                {"type": "TXT", "host": "new", "answer": "drift", "ttl": 300},
            ]
        }
        diff = self.client.get(f"/api/twin/domains/{self.domain}/diff/")
        self.assertEqual(diff.status_code, 200)
        payload = diff.json()
        self.assertTrue(payload["driftDetected"])
        self.assertEqual(payload["summary"]["MODIFIED"], 1)
        self.assertEqual(payload["summary"]["ADDED"], 1)
