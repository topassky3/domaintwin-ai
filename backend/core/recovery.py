from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from .models import (
    DomainSnapshot,
    Incident,
    IncidentEvent,
    RecoveryAuditEvent,
    RecoveryPlan,
)
from .namecom import NameComAPIError, NameComClient
from .twin import normalize_record, normalize_records, snapshot_fingerprint

ACTION_ORDER = {"UPDATE": 0, "CREATE": 1, "DELETE": 2}


class RecoveryError(Exception):
    status_code = 400


class RecoveryApprovalRequired(RecoveryError):
    status_code = 409


class RecoveryStalePlan(RecoveryError):
    status_code = 409


class RecoveryPlanningError(RecoveryError):
    status_code = 422


def _identity(record: dict[str, Any]) -> tuple[str, str, int]:
    return (record["type"], record["host"], record["priority"])


def _provider_payload(record: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "type": record["type"],
        "host": record["host"],
        "answer": record["answer"],
        "ttl": record["ttl"],
    }
    if record.get("priority"):
        payload["priority"] = record["priority"]
    return payload


def _operation_sort_key(operation: dict[str, Any]) -> tuple[Any, ...]:
    record = operation.get("after") or operation.get("before") or {}
    return (
        ACTION_ORDER[operation["action"]],
        record.get("type") or "",
        record.get("host") or "",
        int(record.get("priority") or 0),
        record.get("answer") or "",
        int(operation.get("recordId") or 0),
    )


def build_recovery_operations(
    baseline_records: list[dict[str, Any]],
    live_raw_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    baseline = normalize_records(baseline_records)
    live_items = [
        {
            "recordId": raw.get("id"),
            "record": normalize_record(raw),
        }
        for raw in live_raw_records
    ]
    live_items.sort(
        key=lambda item: (
            item["record"]["type"],
            item["record"]["host"],
            item["record"]["priority"],
            item["record"]["answer"],
            item["record"]["ttl"],
            int(item["recordId"] or 0),
        )
    )

    baseline_groups: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    live_groups: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for record in baseline:
        baseline_groups[_identity(record)].append(record)
    for item in live_items:
        live_groups[_identity(item["record"])].append(item)

    operations: list[dict[str, Any]] = []
    for key in sorted(set(baseline_groups) | set(live_groups)):
        target_group = baseline_groups.get(key, []).copy()
        current_group = live_groups.get(key, []).copy()

        unmatched_targets = target_group.copy()
        unmatched_current = current_group.copy()

        for target in target_group:
            exact = next(
                (item for item in unmatched_current if item["record"] == target),
                None,
            )
            if exact is not None:
                unmatched_targets.remove(target)
                unmatched_current.remove(exact)

        while unmatched_targets and unmatched_current:
            target = unmatched_targets.pop(0)
            current = unmatched_current.pop(0)
            if current["recordId"] is None:
                raise RecoveryPlanningError(
                    "Provider record id is required to update a changed DNS record."
                )
            operations.append(
                {
                    "action": "UPDATE",
                    "recordId": int(current["recordId"]),
                    "before": current["record"],
                    "after": target,
                }
            )

        for target in unmatched_targets:
            operations.append(
                {
                    "action": "CREATE",
                    "recordId": None,
                    "before": None,
                    "after": target,
                }
            )

        for current in unmatched_current:
            if current["recordId"] is None:
                raise RecoveryPlanningError(
                    "Provider record id is required to delete an unexpected DNS record."
                )
            operations.append(
                {
                    "action": "DELETE",
                    "recordId": int(current["recordId"]),
                    "before": current["record"],
                    "after": None,
                }
            )

    return sorted(operations, key=_operation_sort_key)


def recovery_plan_fingerprint(
    *,
    domain_name: str,
    baseline: DomainSnapshot,
    live_fingerprint: str,
    operations: list[dict[str, Any]],
    incident: Incident | None,
) -> str:
    canonical = json.dumps(
        {
            "domainName": domain_name,
            "baselineSnapshotId": baseline.id,
            "targetFingerprint": baseline.fingerprint,
            "liveFingerprint": live_fingerprint,
            "incidentId": incident.id if incident else None,
            "operations": operations,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def append_recovery_audit(
    plan: RecoveryPlan,
    event_type: str,
    payload: dict[str, Any],
) -> RecoveryAuditEvent:
    current_max = (
        RecoveryAuditEvent.objects.filter(plan=plan).aggregate(max_sequence=Max("sequence"))[
            "max_sequence"
        ]
        or 0
    )
    return RecoveryAuditEvent.objects.create(
        plan=plan,
        sequence=current_max + 1,
        event_type=event_type,
        payload=payload,
    )


def _append_incident_event(
    incident: Incident | None,
    event_type: str,
    payload: dict[str, Any],
) -> IncidentEvent | None:
    if incident is None:
        return None
    current_max = (
        IncidentEvent.objects.filter(incident=incident).aggregate(max_sequence=Max("sequence"))[
            "max_sequence"
        ]
        or 0
    )
    return IncidentEvent.objects.create(
        incident=incident,
        sequence=current_max + 1,
        event_type=event_type,
        payload=payload,
    )


@transaction.atomic
def create_recovery_plan(
    *,
    domain_name: str,
    baseline: DomainSnapshot,
    live_raw_records: list[dict[str, Any]],
    incident: Incident | None = None,
) -> tuple[RecoveryPlan, bool]:
    live = normalize_records(live_raw_records)
    live_fingerprint = snapshot_fingerprint(live)
    operations = build_recovery_operations(baseline.records, live_raw_records)
    fingerprint = recovery_plan_fingerprint(
        domain_name=domain_name,
        baseline=baseline,
        live_fingerprint=live_fingerprint,
        operations=operations,
        incident=incident,
    )
    existing = RecoveryPlan.objects.filter(
        domain_name=domain_name,
        plan_fingerprint=fingerprint,
    ).first()
    if existing:
        return existing, False

    plan = RecoveryPlan.objects.create(
        domain_name=domain_name,
        baseline_snapshot=baseline,
        incident=incident,
        live_fingerprint_before=live_fingerprint,
        target_fingerprint=baseline.fingerprint,
        plan_fingerprint=fingerprint,
        operations=operations,
    )
    append_recovery_audit(
        plan,
        "PLAN_CREATED",
        {
            "operationCount": len(operations),
            "liveFingerprint": live_fingerprint,
            "targetFingerprint": baseline.fingerprint,
        },
    )
    _append_incident_event(
        incident,
        "RECOVERY_PLAN_CREATED",
        {"planId": plan.id, "operationCount": len(operations)},
    )
    return plan, True


@transaction.atomic
def approve_recovery_plan(plan: RecoveryPlan) -> RecoveryPlan:
    plan = RecoveryPlan.objects.select_for_update().get(id=plan.id)
    if plan.status == RecoveryPlan.Status.RECOVERED:
        return plan
    if plan.status == RecoveryPlan.Status.APPROVED:
        return plan
    if plan.status != RecoveryPlan.Status.PREVIEW:
        raise RecoveryApprovalRequired(
            f"Recovery plan in status {plan.status} cannot be approved."
        )
    plan.status = RecoveryPlan.Status.APPROVED
    plan.approved_at = timezone.now()
    plan.save(update_fields=["status", "approved_at", "updated_at"])
    append_recovery_audit(
        plan,
        "PLAN_APPROVED",
        {"approvedAt": plan.approved_at.isoformat()},
    )
    _append_incident_event(plan.incident, "RECOVERY_APPROVED", {"planId": plan.id})
    return plan


def _resolve_incident_after_recovery(plan: RecoveryPlan) -> None:
    incident = plan.incident
    if incident is None:
        return
    incident.refresh_from_db()
    if incident.status != Incident.Status.OPEN:
        return
    incident.status = Incident.Status.RESOLVED
    incident.resolved_at = timezone.now()
    incident.save(update_fields=["status", "resolved_at", "last_seen_at"])
    _append_incident_event(
        incident,
        "RECOVERY_VERIFIED",
        {
            "planId": plan.id,
            "targetFingerprint": plan.target_fingerprint,
        },
    )
    _append_incident_event(
        incident,
        "INCIDENT_RESOLVED",
        {"reason": "RECOVERY_VERIFIED", "planId": plan.id},
    )


def _verification_payload(
    plan: RecoveryPlan,
    actual_records: list[dict[str, Any]],
) -> dict[str, Any]:
    normalized = normalize_records(actual_records)
    actual_fingerprint = snapshot_fingerprint(normalized)
    return {
        "matched": actual_fingerprint == plan.target_fingerprint,
        "expectedFingerprint": plan.target_fingerprint,
        "actualFingerprint": actual_fingerprint,
        "recordCount": len(normalized),
        "actualRecords": normalized,
    }


def _mark_verified_recovered(
    plan: RecoveryPlan,
    verification: dict[str, Any],
    *,
    applied: bool,
) -> RecoveryPlan:
    now = timezone.now()
    plan.status = RecoveryPlan.Status.RECOVERED
    plan.verification = verification
    plan.verified_at = now
    if applied and plan.applied_at is None:
        plan.applied_at = now
    plan.save(
        update_fields=[
            "status",
            "verification",
            "verified_at",
            "applied_at",
            "updated_at",
        ]
    )
    append_recovery_audit(
        plan,
        "VERIFICATION_SUCCEEDED",
        verification,
    )
    append_recovery_audit(
        plan,
        "RECOVERY_COMPLETED",
        {"status": plan.status},
    )
    _resolve_incident_after_recovery(plan)
    return plan


def apply_recovery_plan(
    plan: RecoveryPlan,
    *,
    client: NameComClient | None = None,
) -> RecoveryPlan:
    plan.refresh_from_db()
    if plan.status == RecoveryPlan.Status.RECOVERED:
        return plan
    if plan.status != RecoveryPlan.Status.APPROVED:
        raise RecoveryApprovalRequired(
            "Recovery plan must be explicitly approved before apply."
        )

    client = client or NameComClient()
    current_payload = client.list_records(plan.domain_name)
    current_raw = current_payload.get("records") or []
    current = normalize_records(current_raw)
    current_fingerprint = snapshot_fingerprint(current)

    if current_fingerprint == plan.target_fingerprint:
        verification = _verification_payload(plan, current_raw)
        append_recovery_audit(
            plan,
            "APPLY_SKIPPED_ALREADY_RECOVERED",
            {"actualFingerprint": current_fingerprint},
        )
        return _mark_verified_recovered(plan, verification, applied=False)

    if current_fingerprint != plan.live_fingerprint_before:
        plan.status = RecoveryPlan.Status.STALE
        plan.verification = {
            "matched": False,
            "expectedSourceFingerprint": plan.live_fingerprint_before,
            "actualSourceFingerprint": current_fingerprint,
            "reason": "Live DNS changed after preview; regenerate recovery plan.",
        }
        plan.verified_at = timezone.now()
        plan.save(update_fields=["status", "verification", "verified_at", "updated_at"])
        append_recovery_audit(plan, "PLAN_STALE", plan.verification)
        raise RecoveryStalePlan(
            "Live DNS changed after preview. Regenerate the recovery plan before applying."
        )

    plan.status = RecoveryPlan.Status.APPLYING
    plan.applied_at = timezone.now()
    plan.save(update_fields=["status", "applied_at", "updated_at"])
    append_recovery_audit(
        plan,
        "APPLY_STARTED",
        {"operationCount": len(plan.operations)},
    )
    _append_incident_event(
        plan.incident,
        "RECOVERY_APPLY_STARTED",
        {"planId": plan.id, "operationCount": len(plan.operations)},
    )

    results: list[dict[str, Any]] = []
    success_count = 0
    for index, operation in enumerate(plan.operations, start=1):
        action = operation["action"]
        try:
            if action == "UPDATE":
                response = client.update_record(
                    plan.domain_name,
                    int(operation["recordId"]),
                    _provider_payload(operation["after"]),
                )
            elif action == "CREATE":
                response = client.create_record(
                    plan.domain_name,
                    _provider_payload(operation["after"]),
                )
            elif action == "DELETE":
                response = client.delete_record(
                    plan.domain_name,
                    int(operation["recordId"]),
                )
            else:
                raise RecoveryPlanningError(f"Unsupported recovery action: {action}")

            result = {
                "index": index,
                "action": action,
                "status": "SUCCEEDED",
                "recordId": operation.get("recordId"),
                "response": response,
            }
            success_count += 1
            results.append(result)
            append_recovery_audit(plan, "OPERATION_SUCCEEDED", result)
        except Exception as exc:
            result = {
                "index": index,
                "action": action,
                "status": "FAILED",
                "recordId": operation.get("recordId"),
                "error": str(exc),
                "providerStatus": exc.status_code if isinstance(exc, NameComAPIError) else None,
                "retryable": exc.retryable if isinstance(exc, NameComAPIError) else False,
            }
            results.append(result)
            plan.operation_results = results
            plan.status = (
                RecoveryPlan.Status.PARTIAL if success_count else RecoveryPlan.Status.FAILED
            )
            plan.save(update_fields=["operation_results", "status", "updated_at"])
            append_recovery_audit(plan, "OPERATION_FAILED", result)
            _append_incident_event(
                plan.incident,
                "RECOVERY_PARTIAL" if success_count else "RECOVERY_FAILED",
                {"planId": plan.id, **result},
            )
            return plan

    plan.operation_results = results
    plan.save(update_fields=["operation_results", "updated_at"])

    verify_payload = client.list_records(plan.domain_name)
    verify_raw = verify_payload.get("records") or []
    verification = _verification_payload(plan, verify_raw)
    plan.verification = verification
    plan.verified_at = timezone.now()

    if verification["matched"]:
        plan.save(update_fields=["verification", "verified_at", "updated_at"])
        return _mark_verified_recovered(plan, verification, applied=True)

    plan.status = RecoveryPlan.Status.PARTIAL
    plan.save(update_fields=["status", "verification", "verified_at", "updated_at"])
    append_recovery_audit(plan, "VERIFICATION_FAILED", verification)
    _append_incident_event(
        plan.incident,
        "RECOVERY_PARTIAL",
        {"planId": plan.id, "reason": "POST_RECOVERY_VERIFICATION_FAILED"},
    )
    return plan
