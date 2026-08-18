from __future__ import annotations

import hashlib
import json
from typing import Any

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from .models import DomainSnapshot, HealthObservation, Incident, IncidentEvent

DANGEROUS_DNS_RULES = {
    "ADDRESS_RECORD_CHANGED",
    "MX_REMOVED",
    "NS_MODIFIED",
}


def record_health_observation(domain_name: str, health: dict[str, Any]) -> HealthObservation:
    return HealthObservation.objects.create(
        domain_name=domain_name,
        dns_resolution=health.get("dnsResolution") or {},
        http=health.get("http") or {},
        https=health.get("https") or {},
        availability_ok=bool(health.get("availabilityOk")),
    )


def unknown_destination_detected(
    baseline_records: list[dict[str, Any]],
    diff: dict[str, Any],
) -> bool:
    trusted_answers = {
        str(record.get("answer", "")).strip().rstrip(".")
        for record in baseline_records
        if str(record.get("type", "")).upper() in {"A", "AAAA", "CNAME"}
    }
    for change in diff.get("changes", []):
        if str(change.get("state", "")).upper() not in {"ADDED", "MODIFIED"}:
            continue
        after = change.get("after") or {}
        if str(after.get("type", "")).upper() not in {"A", "AAAA", "CNAME"}:
            continue
        answer = str(after.get("answer", "")).strip().rstrip(".")
        if answer and answer not in trusted_answers:
            return True
    return False


def incident_required(
    *,
    drift_detected: bool,
    availability_failed: bool,
    risk: dict[str, Any],
) -> bool:
    dangerous_dns = any(
        factor.get("ruleId") in DANGEROUS_DNS_RULES
        for factor in risk.get("factors", [])
    )
    return bool(
        dangerous_dns
        or risk.get("score", 0) >= 50
        or (drift_detected and availability_failed)
    )


def monitor_state(
    *,
    drift_detected: bool,
    availability_failed: bool,
    risk: dict[str, Any],
) -> str:
    if incident_required(
        drift_detected=drift_detected,
        availability_failed=availability_failed,
        risk=risk,
    ):
        return "INCIDENT"
    if drift_detected or availability_failed:
        return "DEGRADED"
    return "HEALTHY"


def evidence_fingerprint(
    *,
    baseline: DomainSnapshot,
    live_fingerprint: str,
    diff: dict[str, Any],
    health: dict[str, Any],
    unknown_destination: bool,
    risk: dict[str, Any],
) -> str:
    signature = {
        "baselineFingerprint": baseline.fingerprint,
        "liveFingerprint": live_fingerprint,
        "diff": diff,
        "health": {
            "dnsResolutionOk": bool((health.get("dnsResolution") or {}).get("ok")),
            "httpOk": bool((health.get("http") or {}).get("ok")),
            "httpStatus": (health.get("http") or {}).get("statusCode"),
            "httpsOk": bool((health.get("https") or {}).get("ok")),
            "httpsStatus": (health.get("https") or {}).get("statusCode"),
            "availabilityFailed": bool(health.get("availabilityFailed")),
        },
        "unknownDestination": unknown_destination,
        "risk": {
            "ruleVersion": risk.get("ruleVersion"),
            "score": risk.get("score"),
            "severity": risk.get("severity"),
            "factors": risk.get("factors", []),
        },
    }
    canonical = json.dumps(signature, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_incident_evidence(
    *,
    baseline: DomainSnapshot,
    live_fingerprint: str,
    diff: dict[str, Any],
    health: dict[str, Any],
    observation: HealthObservation,
    unknown_destination: bool,
    risk: dict[str, Any],
) -> dict[str, Any]:
    return {
        "baseline": {
            "snapshotId": baseline.id,
            "version": baseline.version,
            "fingerprint": baseline.fingerprint,
        },
        "liveFingerprint": live_fingerprint,
        "diff": diff,
        "health": {
            "observationId": observation.id,
            "checkedAt": observation.checked_at.isoformat(),
            "dnsResolution": health.get("dnsResolution") or {},
            "http": health.get("http") or {},
            "https": health.get("https") or {},
            "availabilityOk": bool(health.get("availabilityOk")),
            "availabilityFailed": bool(health.get("availabilityFailed")),
        },
        "unknownDestination": unknown_destination,
        "riskRuleVersion": risk.get("ruleVersion"),
    }


def _append_event(incident: Incident, event_type: str, payload: dict[str, Any]) -> IncidentEvent:
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
def correlate_incident(
    *,
    domain_name: str,
    baseline: DomainSnapshot,
    live_fingerprint: str,
    diff: dict[str, Any],
    health: dict[str, Any],
    observation: HealthObservation,
    unknown_destination: bool,
    risk: dict[str, Any],
) -> tuple[str, Incident | None, bool]:
    drift_detected = any(
        diff.get("summary", {}).get(state, 0) > 0
        for state in ("ADDED", "REMOVED", "MODIFIED")
    )
    availability_failed = bool(health.get("availabilityFailed"))
    state = monitor_state(
        drift_detected=drift_detected,
        availability_failed=availability_failed,
        risk=risk,
    )
    should_open = state == "INCIDENT"
    signature = evidence_fingerprint(
        baseline=baseline,
        live_fingerprint=live_fingerprint,
        diff=diff,
        health=health,
        unknown_destination=unknown_destination,
        risk=risk,
    )
    evidence = build_incident_evidence(
        baseline=baseline,
        live_fingerprint=live_fingerprint,
        diff=diff,
        health=health,
        observation=observation,
        unknown_destination=unknown_destination,
        risk=risk,
    )

    active = (
        Incident.objects.select_for_update()
        .filter(domain_name=domain_name, status=Incident.Status.OPEN)
        .first()
    )

    if not should_open:
        if active:
            active.status = Incident.Status.RESOLVED
            active.resolved_at = timezone.now()
            active.evidence = evidence
            active.score = int(risk.get("score", 0))
            active.severity = str(risk.get("severity", "LOW"))
            active.factors = risk.get("factors", [])
            active.evidence_fingerprint = signature
            active.save()
            _append_event(
                active,
                "INCIDENT_RESOLVED",
                {
                    "state": state,
                    "score": active.score,
                    "severity": active.severity,
                    "driftDetected": drift_detected,
                    "availabilityFailed": availability_failed,
                },
            )
            return state, active, False
        return state, None, False

    if active is None:
        active = Incident.objects.create(
            domain_name=domain_name,
            baseline_snapshot=baseline,
            score=int(risk.get("score", 0)),
            severity=str(risk.get("severity", "LOW")),
            factors=risk.get("factors", []),
            evidence=evidence,
            evidence_fingerprint=signature,
        )
        _append_event(
            active,
            "DNS_EVIDENCE_CAPTURED",
            {"driftDetected": drift_detected, "summary": diff.get("summary", {})},
        )
        _append_event(
            active,
            "HEALTH_EVIDENCE_CAPTURED",
            {
                "observationId": observation.id,
                "availabilityFailed": availability_failed,
                "httpOk": bool((health.get("http") or {}).get("ok")),
                "httpsOk": bool((health.get("https") or {}).get("ok")),
            },
        )
        _append_event(
            active,
            "INCIDENT_OPENED",
            {
                "score": active.score,
                "severity": active.severity,
                "factorCount": len(active.factors),
            },
        )
        return state, active, True

    changed = active.evidence_fingerprint != signature
    active.baseline_snapshot = baseline
    active.score = int(risk.get("score", 0))
    active.severity = str(risk.get("severity", "LOW"))
    active.factors = risk.get("factors", [])
    active.evidence = evidence
    active.evidence_fingerprint = signature
    active.save()

    if changed:
        _append_event(
            active,
            "INCIDENT_UPDATED",
            {
                "score": active.score,
                "severity": active.severity,
                "driftDetected": drift_detected,
                "availabilityFailed": availability_failed,
                "factorCount": len(active.factors),
            },
        )
    return state, active, False
