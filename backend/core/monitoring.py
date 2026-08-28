from __future__ import annotations

from time import perf_counter
from typing import Any, Callable

from django.http import Http404
from django.utils import timezone

from .health import check_domain_health
from .incidents import (
    correlate_incident,
    record_health_observation,
    unknown_destination_detected,
)
from .models import KnownGoodSnapshot, ManagedDomain, ProviderConnection
from .namecom import NameComClient
from .risk import evaluate_risk
from .tenant import require_snapshot_domain
from .twin import diff_records, normalize_records, snapshot_fingerprint


HealthChecker = Callable[[str], dict[str, Any]]
ClientFactory = Callable[[], NameComClient]


def evaluate_domain_state(
    domain_name: str,
    *,
    client: NameComClient | None = None,
    health_checker: HealthChecker | None = None,
) -> dict[str, Any]:
    """Evaluate one domain using the same deterministic pipeline as the HTTP API.

    P5 keeps one source of truth for manual and automatic evaluation: known-good DNS
    evidence, live provider records, external availability, deterministic risk and
    incident correlation. No scheduler-specific evidence model is introduced.
    """

    marker = (
        KnownGoodSnapshot.objects.select_related("snapshot")
        .filter(domain_name=domain_name)
        .first()
    )
    if marker is None:
        raise Http404("Known-good snapshot not found.")
    baseline = require_snapshot_domain(marker.snapshot, domain_name)

    provider = client or NameComClient()
    payload = provider.list_records(domain_name)
    raw_records = payload.get("records") or []
    if not isinstance(raw_records, list):
        raw_records = list(raw_records) if raw_records else []

    live = normalize_records(raw_records)
    diff = diff_records(baseline.records, live)
    live_fingerprint = snapshot_fingerprint(live)
    drift_detected = any(
        diff["summary"][state] > 0
        for state in ("ADDED", "REMOVED", "MODIFIED")
    )

    checker = health_checker or check_domain_health
    health = checker(domain_name)
    observation = record_health_observation(health["domainName"], health)
    unknown_destination = unknown_destination_detected(baseline.records, diff)
    risk = evaluate_risk(
        diff,
        http_health_failed=bool(health["availabilityFailed"]),
        unknown_destination=unknown_destination,
    )
    state, incident, created = correlate_incident(
        domain_name=domain_name,
        baseline=baseline,
        live_fingerprint=live_fingerprint,
        diff=diff,
        health=health,
        observation=observation,
        unknown_destination=unknown_destination,
        risk=risk,
    )

    return {
        "domainName": domain_name,
        "state": state,
        "baseline": baseline,
        "liveFingerprint": live_fingerprint,
        "driftDetected": drift_detected,
        "diff": diff,
        "health": health,
        "observation": observation,
        "unknownDestination": unknown_destination,
        "risk": risk,
        "incident": incident,
        "incidentCreated": created,
    }


def _candidate_domains(
    *,
    organization_slug: str | None = None,
    domain_names: list[str] | tuple[str, ...] | None = None,
):
    rows = ManagedDomain.objects.select_related("organization").filter(
        is_active=True,
        organization__is_active=True,
    )
    if organization_slug:
        rows = rows.filter(organization__slug=organization_slug)
    if domain_names:
        rows = rows.filter(name__in=domain_names)
    return rows.order_by("organization__slug", "name")


def run_monitoring_cycle(
    *,
    organization_slug: str | None = None,
    domain_names: list[str] | tuple[str, ...] | None = None,
    client_factory: ClientFactory = NameComClient,
    health_checker: HealthChecker = check_domain_health,
) -> dict[str, Any]:
    """Run one scheduler-friendly monitoring pass across eligible managed domains.

    Failures are isolated per domain. A missing provider binding or known-good baseline
    is a deliberate skip and never causes a provider call. This makes a one-shot cycle
    safe for cron/Task Scheduler while preserving the P3/P4 tenant/provider boundaries.
    """

    started_at = timezone.now()
    started_clock = perf_counter()
    results: list[dict[str, Any]] = []
    counts = {
        "checked": 0,
        "healthy": 0,
        "degraded": 0,
        "incident": 0,
        "skipped": 0,
        "failed": 0,
    }

    for managed_domain in _candidate_domains(
        organization_slug=organization_slug,
        domain_names=domain_names,
    ):
        base = {
            "organizationId": str(managed_domain.organization_id),
            "organizationSlug": managed_domain.organization.slug,
            "domainName": managed_domain.name,
        }

        provider_enabled = ProviderConnection.objects.filter(
            organization=managed_domain.organization,
            provider=ProviderConnection.Provider.NAMECOM,
            is_active=True,
        ).exists()
        if not provider_enabled:
            counts["skipped"] += 1
            results.append(
                {
                    **base,
                    "outcome": "SKIPPED",
                    "reason": "PROVIDER_CONNECTION_REQUIRED",
                }
            )
            continue

        if not KnownGoodSnapshot.objects.filter(domain_name=managed_domain.name).exists():
            counts["skipped"] += 1
            results.append(
                {
                    **base,
                    "outcome": "SKIPPED",
                    "reason": "KNOWN_GOOD_BASELINE_REQUIRED",
                }
            )
            continue

        try:
            evaluation = evaluate_domain_state(
                managed_domain.name,
                client=client_factory(),
                health_checker=health_checker,
            )
        except Exception as exc:  # isolate one provider/health failure from other tenants/domains
            counts["failed"] += 1
            results.append(
                {
                    **base,
                    "outcome": "FAILED",
                    "errorType": exc.__class__.__name__,
                    "error": str(exc),
                }
            )
            continue

        state = str(evaluation["state"]).upper()
        counts["checked"] += 1
        if state == "HEALTHY":
            counts["healthy"] += 1
        elif state == "DEGRADED":
            counts["degraded"] += 1
        elif state == "INCIDENT":
            counts["incident"] += 1

        incident = evaluation["incident"]
        results.append(
            {
                **base,
                "outcome": "CHECKED",
                "state": state,
                "driftDetected": bool(evaluation["driftDetected"]),
                "availabilityFailed": bool(evaluation["health"].get("availabilityFailed")),
                "riskScore": int(evaluation["risk"].get("score", 0)),
                "severity": str(evaluation["risk"].get("severity", "LOW")),
                "incidentId": incident.id if incident else None,
                "incidentCreated": bool(evaluation["incidentCreated"]),
                "observationId": evaluation["observation"].id,
            }
        )

    completed_at = timezone.now()
    return {
        "startedAt": started_at.isoformat(),
        "completedAt": completed_at.isoformat(),
        "durationMs": round((perf_counter() - started_clock) * 1000, 2),
        **counts,
        "results": results,
    }
