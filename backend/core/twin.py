from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any

from django.db import transaction
from django.db.models import Max

from .models import DomainSnapshot, KnownGoodSnapshot

CANONICAL_FIELDS = ("type", "host", "answer", "ttl", "priority")


def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "type": str(record.get("type", "")).upper().strip(),
        "host": str(record.get("host", "")).strip().rstrip("."),
        "answer": str(record.get("answer", "")).strip().rstrip("."),
        "ttl": int(record.get("ttl") or 0),
        "priority": int(record.get("priority") or 0),
    }
    return normalized


def normalize_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = [normalize_record(record) for record in records]
    return sorted(
        normalized,
        key=lambda item: (
            item["type"],
            item["host"],
            item["priority"],
            item["answer"],
            item["ttl"],
        ),
    )


def snapshot_fingerprint(records: list[dict[str, Any]]) -> str:
    canonical = json.dumps(records, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _identity(record: dict[str, Any]) -> tuple[str, str, int]:
    return (record["type"], record["host"], record["priority"])


def diff_records(
    before_records: list[dict[str, Any]],
    after_records: list[dict[str, Any]],
) -> dict[str, Any]:
    before = normalize_records(before_records)
    after = normalize_records(after_records)

    before_groups: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    after_groups: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for record in before:
        before_groups[_identity(record)].append(record)
    for record in after:
        after_groups[_identity(record)].append(record)

    changes: list[dict[str, Any]] = []
    all_keys = sorted(set(before_groups) | set(after_groups))

    for key in all_keys:
        old = before_groups.get(key, [])
        new = after_groups.get(key, [])

        unmatched_old = old.copy()
        unmatched_new = new.copy()

        for record in old:
            if record in unmatched_new:
                changes.append({"state": "UNCHANGED", "before": record, "after": record})
                unmatched_old.remove(record)
                unmatched_new.remove(record)

        while unmatched_old and unmatched_new:
            old_record = unmatched_old.pop(0)
            new_record = unmatched_new.pop(0)
            changes.append({"state": "MODIFIED", "before": old_record, "after": new_record})

        for record in unmatched_old:
            changes.append({"state": "REMOVED", "before": record, "after": None})
        for record in unmatched_new:
            changes.append({"state": "ADDED", "before": None, "after": record})

    summary = {state: 0 for state in ("ADDED", "REMOVED", "MODIFIED", "UNCHANGED")}
    for change in changes:
        summary[change["state"]] += 1

    return {"summary": summary, "changes": changes}


@transaction.atomic
def create_snapshot(domain_name: str, raw_records: list[dict[str, Any]]) -> DomainSnapshot:
    records = normalize_records(raw_records)
    current_max = (
        DomainSnapshot.objects.select_for_update()
        .filter(domain_name=domain_name)
        .aggregate(max_version=Max("version"))["max_version"]
        or 0
    )
    return DomainSnapshot.objects.create(
        domain_name=domain_name,
        version=current_max + 1,
        records=records,
        fingerprint=snapshot_fingerprint(records),
    )


@transaction.atomic
def mark_known_good(snapshot: DomainSnapshot) -> KnownGoodSnapshot:
    marker, _ = KnownGoodSnapshot.objects.update_or_create(
        domain_name=snapshot.domain_name,
        defaults={"snapshot": snapshot},
    )
    return marker
