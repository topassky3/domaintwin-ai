from __future__ import annotations

import hashlib
import json
import re
import uuid
from typing import Any

from django.db.models import Max
from django.utils import timezone

from .models import EmergencyDomainAuditEvent, EmergencyDomainPlan, KnownGoodSnapshot
from .namecom import NameComAPIError, NameComClient
from .recovery import build_recovery_operations
from .twin import normalize_record, normalize_records, snapshot_fingerprint

SUPPORTED_TLDS = {"com", "net", "org"}
DOMAIN_RE = re.compile(r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


class EmergencyDomainError(Exception):
    status_code = 400


class EmergencyDomainNotAvailable(EmergencyDomainError):
    status_code = 409


class EmergencyDomainUnsupported(EmergencyDomainError):
    status_code = 422


class EmergencyDomainApprovalRequired(EmergencyDomainError):
    status_code = 409


class EmergencyDomainStale(EmergencyDomainError):
    status_code = 409


def normalize_domain_name(value: str) -> str:
    domain = value.strip().lower().rstrip(".")
    if not DOMAIN_RE.fullmatch(domain):
        raise EmergencyDomainUnsupported("Enter a valid ASCII domain name such as rescue-example.com.")
    tld = domain.rsplit(".", 1)[-1]
    if tld not in SUPPORTED_TLDS:
        raise EmergencyDomainUnsupported(
            f"Gate 8 currently limits registration to: {', '.join(sorted(SUPPORTED_TLDS))}."
        )
    return domain


def sanitize_search_keyword(value: str) -> str:
    keyword = value.strip().lower()
    if not keyword or len(keyword) > 253:
        raise EmergencyDomainUnsupported("Search keyword must contain 1 to 253 characters.")
    if any(char.isspace() for char in keyword):
        raise EmergencyDomainUnsupported("Search keyword cannot contain spaces.")
    return keyword


def sanitize_tld_filter(values: list[str] | None) -> list[str]:
    requested = values or ["com", "net", "org"]
    cleaned: list[str] = []
    for raw in requested:
        tld = str(raw).strip().lower().lstrip(".")
        if tld in SUPPORTED_TLDS and tld not in cleaned:
            cleaned.append(tld)
    if not cleaned:
        raise EmergencyDomainUnsupported("At least one supported TLD is required.")
    return cleaned


def _safe_search_result(raw: dict[str, Any]) -> dict[str, Any]:
    purchase_type = raw.get("purchaseType") or "registration"
    purchasable = bool(raw.get("purchasable"))
    premium = bool(raw.get("premium"))
    return {
        "domainName": raw.get("domainName"),
        "purchasable": purchasable,
        "sld": raw.get("sld"),
        "tld": raw.get("tld"),
        "premium": premium,
        "purchasePrice": raw.get("purchasePrice"),
        "renewalPrice": raw.get("renewalPrice"),
        "purchaseType": purchase_type,
        "reason": raw.get("reason") or "",
        "gate8Supported": purchasable and purchase_type == "registration" and not premium,
    }


def search_candidates(
    client: NameComClient,
    *,
    keyword: str,
    tld_filter: list[str] | None = None,
) -> list[dict[str, Any]]:
    payload = client.search_domains(
        keyword=sanitize_search_keyword(keyword),
        tld_filter=sanitize_tld_filter(tld_filter),
    )
    return [_safe_search_result(row) for row in payload.get("results") or [] if isinstance(row, dict)]


def check_candidate(client: NameComClient, domain_name: str) -> dict[str, Any]:
    domain = normalize_domain_name(domain_name)
    payload = client.check_availability([domain])
    rows = [row for row in payload.get("results") or [] if isinstance(row, dict)]
    exact = next((row for row in rows if str(row.get("domainName", "")).lower() == domain), None)
    if exact is None:
        raise EmergencyDomainNotAvailable("name.com did not return an exact availability result.")
    return _safe_search_result(exact)


def _preview_operations(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"action": "CREATE", "recordId": None, "before": None, "after": record}
        for record in normalize_records(records)
    ]


def _plan_fingerprint(
    *,
    source_domain: str,
    target_domain: str,
    baseline_id: int,
    baseline_fingerprint: str,
    availability: dict[str, Any],
) -> str:
    canonical = json.dumps(
        {
            "sourceDomain": source_domain,
            "targetDomain": target_domain,
            "baselineSnapshotId": baseline_id,
            "baselineFingerprint": baseline_fingerprint,
            "purchaseType": availability.get("purchaseType"),
            "premium": availability.get("premium"),
            "purchasePrice": availability.get("purchasePrice"),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def append_emergency_audit(
    plan: EmergencyDomainPlan,
    event_type: str,
    payload: dict[str, Any],
) -> EmergencyDomainAuditEvent:
    current_max = (
        EmergencyDomainAuditEvent.objects.filter(plan=plan).aggregate(max_sequence=Max("sequence"))[
            "max_sequence"
        ]
        or 0
    )
    return EmergencyDomainAuditEvent.objects.create(
        plan=plan,
        sequence=current_max + 1,
        event_type=event_type,
        payload=payload,
    )


def create_emergency_plan(
    *,
    source_domain: str,
    target_domain: str,
    client: NameComClient,
) -> tuple[EmergencyDomainPlan, bool]:
    source = source_domain.strip().lower().rstrip(".")
    target = normalize_domain_name(target_domain)
    if source == target:
        raise EmergencyDomainUnsupported("Emergency domain must be different from the source domain.")

    marker = KnownGoodSnapshot.objects.select_related("snapshot").filter(domain_name=source).first()
    if marker is None:
        raise EmergencyDomainUnsupported("Source domain does not have a known-good snapshot.")
    baseline = marker.snapshot

    availability = check_candidate(client, target)
    if not availability["purchasable"]:
        raise EmergencyDomainNotAvailable(availability.get("reason") or "Target domain is not purchasable.")
    if availability.get("purchaseType") != "registration":
        raise EmergencyDomainUnsupported("Gate 8 supports standard registration inventory only.")
    if availability.get("premium"):
        raise EmergencyDomainUnsupported(
            "Premium domains are intentionally excluded from Gate 8 to avoid unreviewed premium pricing."
        )

    fingerprint = _plan_fingerprint(
        source_domain=source,
        target_domain=target,
        baseline_id=baseline.id,
        baseline_fingerprint=baseline.fingerprint,
        availability=availability,
    )
    existing = EmergencyDomainPlan.objects.filter(
        source_domain_name=source,
        target_domain_name=target,
        plan_fingerprint=fingerprint,
        status__in=[
            EmergencyDomainPlan.Status.PREVIEW,
            EmergencyDomainPlan.Status.APPROVED,
            EmergencyDomainPlan.Status.APPLYING,
            EmergencyDomainPlan.Status.READY,
        ],
    ).first()
    if existing:
        return existing, False

    plan = EmergencyDomainPlan.objects.create(
        source_domain_name=source,
        target_domain_name=target,
        baseline_snapshot=baseline,
        availability=availability,
        expected_fingerprint=baseline.fingerprint,
        plan_fingerprint=fingerprint,
        idempotency_key=str(uuid.uuid4()),
        operations=_preview_operations(baseline.records),
    )
    append_emergency_audit(
        plan,
        "PLAN_CREATED",
        {
            "sourceDomain": source,
            "targetDomain": target,
            "baselineSnapshotId": baseline.id,
            "baselineVersion": baseline.version,
            "recordCount": len(plan.operations),
            "purchasePrice": availability.get("purchasePrice"),
        },
    )
    return plan, True


def approve_emergency_plan(plan: EmergencyDomainPlan) -> EmergencyDomainPlan:
    if plan.status == EmergencyDomainPlan.Status.APPROVED:
        return plan
    if plan.status != EmergencyDomainPlan.Status.PREVIEW:
        raise EmergencyDomainApprovalRequired(
            f"Only PREVIEW plans can be approved; current status is {plan.status}."
        )
    plan.status = EmergencyDomainPlan.Status.APPROVED
    plan.approved_at = timezone.now()
    plan.save(update_fields=["status", "approved_at", "updated_at"])
    append_emergency_audit(plan, "PLAN_APPROVED", {"targetDomain": plan.target_domain_name})
    return plan


def _provider_record_payload(record: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "type": record["type"],
        "host": record["host"],
        "answer": record["answer"],
        "ttl": record["ttl"],
    }
    if record.get("priority"):
        payload["priority"] = record["priority"]
    return payload


def _safe_registration(raw: dict[str, Any], target_domain: str) -> dict[str, Any]:
    domain = raw.get("domain") if isinstance(raw.get("domain"), dict) else {}
    return {
        "domainName": domain.get("domainName") or target_domain,
        "createDate": domain.get("createDate"),
        "expireDate": domain.get("expireDate"),
        "autorenewEnabled": domain.get("autorenewEnabled"),
        "locked": domain.get("locked"),
        "privacyEnabled": domain.get("privacyEnabled"),
        "order": raw.get("order"),
        "totalPaid": raw.get("totalPaid"),
    }


def _mark_failed(
    plan: EmergencyDomainPlan,
    *,
    status: str,
    event_type: str,
    message: str,
) -> EmergencyDomainPlan:
    plan.status = status
    plan.verification = {**(plan.verification or {}), "matched": False, "error": message}
    plan.save(update_fields=["status", "verification", "updated_at"])
    append_emergency_audit(plan, event_type, {"message": message})
    return plan


def _registration_payload(plan: EmergencyDomainPlan) -> dict[str, Any]:
    return {
        "domain": {"domainName": plan.target_domain_name},
        "purchaseType": "registration",
        "years": 1,
    }


def apply_emergency_plan(
    plan: EmergencyDomainPlan,
    *,
    client: NameComClient,
) -> EmergencyDomainPlan:
    if plan.status == EmergencyDomainPlan.Status.READY:
        return plan
    if plan.status not in {
        EmergencyDomainPlan.Status.APPROVED,
        EmergencyDomainPlan.Status.APPLYING,
    }:
        raise EmergencyDomainApprovalRequired(
            f"Emergency domain apply requires APPROVED/APPLYING status; current status is {plan.status}."
        )

    first_attempt = plan.status == EmergencyDomainPlan.Status.APPROVED
    if first_attempt:
        current = check_candidate(client, plan.target_domain_name)
        if not current.get("purchasable") or current.get("purchaseType") != "registration" or current.get("premium"):
            _mark_failed(
                plan,
                status=EmergencyDomainPlan.Status.STALE,
                event_type="AVAILABILITY_RECHECK_FAILED",
                message="Target domain availability or pricing class changed before registration.",
            )
            raise EmergencyDomainStale("Target domain availability changed; create a new preview.")

        plan.status = EmergencyDomainPlan.Status.APPLYING
        plan.applied_at = timezone.now()
        plan.save(update_fields=["status", "applied_at", "updated_at"])
        append_emergency_audit(
            plan,
            "REGISTRATION_STARTED",
            {"targetDomain": plan.target_domain_name, "environment": client.environment},
        )
    else:
        append_emergency_audit(
            plan,
            "APPLY_RESUMED",
            {
                "targetDomain": plan.target_domain_name,
                "registrationPersisted": bool(plan.registration),
            },
        )

    if not plan.registration:
        if not first_attempt:
            append_emergency_audit(
                plan,
                "REGISTRATION_RETRY",
                {"targetDomain": plan.target_domain_name},
            )
        registration_raw = client.create_domain(
            _registration_payload(plan),
            idempotency_key=plan.idempotency_key,
        )
        plan.registration = _safe_registration(registration_raw, plan.target_domain_name)
        plan.save(update_fields=["registration", "updated_at"])
        append_emergency_audit(
            plan,
            "DOMAIN_REGISTERED",
            {
                "targetDomain": plan.target_domain_name,
                "order": plan.registration.get("order"),
                "totalPaid": plan.registration.get("totalPaid"),
            },
        )

    live_payload = client.list_records(plan.target_domain_name)
    live_raw = live_payload.get("records") or []
    actual_operations = build_recovery_operations(plan.baseline_snapshot.records, live_raw)
    unsafe_operations = [row for row in actual_operations if row.get("action") != "CREATE"]
    if unsafe_operations:
        return _mark_failed(
            plan,
            status=EmergencyDomainPlan.Status.PARTIAL,
            event_type="CLONE_ABORTED_UNEXPECTED_TARGET_STATE",
            message="Fresh target contains records that would require UPDATE or DELETE; no unpreviewed mutation was executed.",
        )

    plan.operations = actual_operations
    plan.save(update_fields=["operations", "updated_at"])
    append_emergency_audit(plan, "CLONE_STARTED", {"operationCount": len(actual_operations)})

    results = list(plan.operation_results or [])
    for operation in actual_operations:
        desired = operation.get("after") or {}
        try:
            created = client.create_record(plan.target_domain_name, _provider_record_payload(desired))
            normalized = normalize_record(created)
            result = {
                "action": "CREATE",
                "status": "SUCCEEDED",
                "recordId": created.get("id"),
                "record": normalized,
            }
            results.append(result)
            plan.operation_results = results
            plan.save(update_fields=["operation_results", "updated_at"])
            append_emergency_audit(
                plan,
                "DNS_RECORD_CLONED",
                {
                    "recordId": created.get("id"),
                    "type": normalized["type"],
                    "host": normalized["host"],
                },
            )
        except NameComAPIError as exc:
            results.append(
                {
                    "action": "CREATE",
                    "status": "FAILED",
                    "record": desired,
                    "error": exc.message,
                    "retryable": exc.retryable,
                }
            )
            plan.operation_results = results
            plan.save(update_fields=["operation_results", "updated_at"])
            if exc.retryable:
                append_emergency_audit(
                    plan,
                    "DNS_CLONE_RETRYABLE_FAILURE",
                    {"message": exc.message},
                )
                raise
            return _mark_failed(
                plan,
                status=EmergencyDomainPlan.Status.PARTIAL,
                event_type="DNS_CLONE_PARTIAL",
                message=exc.message,
            )

    verified_raw = client.list_records(plan.target_domain_name).get("records") or []
    normalized_verified = normalize_records(verified_raw)
    actual_fingerprint = snapshot_fingerprint(normalized_verified)
    matched = actual_fingerprint == plan.expected_fingerprint
    plan.actual_fingerprint = actual_fingerprint
    plan.verified_at = timezone.now()
    plan.verification = {
        "matched": matched,
        "expectedFingerprint": plan.expected_fingerprint,
        "actualFingerprint": actual_fingerprint,
        "recordCount": len(normalized_verified),
    }
    plan.status = EmergencyDomainPlan.Status.READY if matched else EmergencyDomainPlan.Status.FAILED
    plan.save(
        update_fields=[
            "actual_fingerprint",
            "verified_at",
            "verification",
            "status",
            "updated_at",
        ]
    )
    append_emergency_audit(
        plan,
        "CLONE_VERIFIED" if matched else "CLONE_VERIFICATION_FAILED",
        plan.verification,
    )
    if matched:
        append_emergency_audit(
            plan,
            "EMERGENCY_DOMAIN_READY",
            {"targetDomain": plan.target_domain_name},
        )
    return plan
