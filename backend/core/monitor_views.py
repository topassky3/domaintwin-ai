from __future__ import annotations

from django.db.models import F
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from .health import UnsafeHealthTarget, check_domain_health
from .models import HealthObservation, Incident
from .monitoring import evaluate_domain_state
from .namecom import NameComAPIError, NameComClient
from .tenant import TenantContextError, tenant_error_response, tenant_scoped_queryset


def _cors(response: JsonResponse) -> JsonResponse:
    response["Access-Control-Allow-Origin"] = "http://localhost:3000"
    response["Access-Control-Allow-Headers"] = "Content-Type,X-CSRFToken"
    response["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response


def _json(data: dict, status: int = 200) -> JsonResponse:
    return _cors(JsonResponse(data, status=status))


def _error_response(exc: Exception) -> JsonResponse:
    if isinstance(exc, TenantContextError):
        return _cors(tenant_error_response(exc))
    if isinstance(exc, UnsafeHealthTarget):
        return _json({"error": {"message": str(exc), "status": 400}}, status=400)
    if isinstance(exc, Http404):
        return _json({"error": {"message": "Resource not found.", "status": 404}}, status=404)
    if isinstance(exc, NameComAPIError):
        return _json(
            {
                "error": {
                    "message": exc.message,
                    "details": exc.details,
                    "status": exc.status_code,
                    "retryable": exc.retryable,
                }
            },
            status=exc.status_code if 400 <= exc.status_code <= 599 else 502,
        )
    return _json({"error": {"message": str(exc), "status": 500}}, status=500)


def _serialize_health(observation: HealthObservation) -> dict:
    return {
        "id": observation.id,
        "domainName": observation.domain_name,
        "dnsResolution": observation.dns_resolution,
        "http": observation.http,
        "https": observation.https,
        "availabilityOk": observation.availability_ok,
        "availabilityFailed": not observation.availability_ok,
        "checkedAt": observation.checked_at.isoformat(),
    }


def _serialize_incident(incident: Incident, *, include_timeline: bool = False) -> dict:
    payload = {
        "id": incident.id,
        "domainName": incident.domain_name,
        "status": incident.status,
        "baselineSnapshotId": incident.baseline_snapshot_id,
        "score": incident.score,
        "severity": incident.severity,
        "factorCount": len(incident.factors),
        "factors": incident.factors,
        "evidence": incident.evidence,
        "evidenceFingerprint": incident.evidence_fingerprint,
        "openedAt": incident.opened_at.isoformat(),
        "lastSeenAt": incident.last_seen_at.isoformat(),
        "resolvedAt": incident.resolved_at.isoformat() if incident.resolved_at else None,
    }
    if include_timeline:
        payload["timeline"] = [
            {
                "sequence": event.sequence,
                "eventType": event.event_type,
                "payload": event.payload,
                "occurredAt": event.occurred_at.isoformat(),
            }
            for event in incident.timeline.all()
        ]
    return payload


@require_http_methods(["GET", "OPTIONS"])
def domain_health(request, domain_name: str):
    if request.method == "OPTIONS":
        return _json({})
    try:
        health = check_domain_health(domain_name)
        from .incidents import record_health_observation

        observation = record_health_observation(health["domainName"], health)
        return _json({"health": _serialize_health(observation)})
    except Exception as exc:
        return _error_response(exc)


@require_http_methods(["POST", "OPTIONS"])
def evaluate_domain(request, domain_name: str):
    if request.method == "OPTIONS":
        return _json({})
    try:
        evaluation = evaluate_domain_state(
            domain_name,
            client_factory=NameComClient,
            health_checker=check_domain_health,
        )
        baseline = evaluation["baseline"]
        incident = evaluation["incident"]
        return _json(
            {
                "domainName": domain_name,
                "state": evaluation["state"],
                "baselineSnapshotId": baseline.id,
                "baselineVersion": baseline.version,
                "baselineFingerprint": baseline.fingerprint,
                "liveFingerprint": evaluation["liveFingerprint"],
                "driftDetected": evaluation["driftDetected"],
                "diff": evaluation["diff"],
                "health": _serialize_health(evaluation["observation"]),
                "unknownDestination": evaluation["unknownDestination"],
                "risk": evaluation["risk"],
                "incidentCreated": evaluation["incidentCreated"],
                "incident": _serialize_incident(incident, include_timeline=True) if incident else None,
            },
            status=201 if evaluation["incidentCreated"] else 200,
        )
    except Exception as exc:
        return _error_response(exc)


@require_http_methods(["GET", "OPTIONS"])
def domain_monitor_status(request, domain_name: str):
    if request.method == "OPTIONS":
        return _json({})
    active = Incident.objects.filter(
        domain_name=domain_name,
        status=Incident.Status.OPEN,
        baseline_snapshot__domain_name=F("domain_name"),
    ).first()
    latest_health = HealthObservation.objects.filter(domain_name=domain_name).first()
    if active:
        state = "INCIDENT"
    elif latest_health and not latest_health.availability_ok:
        state = "DEGRADED"
    else:
        state = "HEALTHY"
    return _json(
        {
            "domainName": domain_name,
            "state": state,
            "monitoringMode": "AUTOMATIC_LITE",
            "activeIncident": _serialize_incident(active) if active else None,
            "latestHealth": _serialize_health(latest_health) if latest_health else None,
        }
    )


@require_http_methods(["GET", "OPTIONS"])
def domain_incidents(request, domain_name: str):
    if request.method == "OPTIONS":
        return _json({})
    rows = Incident.objects.filter(
        domain_name=domain_name,
        baseline_snapshot__domain_name=F("domain_name"),
    )
    return _json(
        {
            "domainName": domain_name,
            "incidents": [_serialize_incident(row) for row in rows],
            "totalCount": rows.count(),
        }
    )


@require_http_methods(["GET", "OPTIONS"])
def incident_detail(request, incident_id: int):
    if request.method == "OPTIONS":
        return _json({})
    try:
        rows = tenant_scoped_queryset(
            request,
            Incident.objects.select_related("baseline_snapshot"),
            domain_lookups=("domain_name", "baseline_snapshot__domain_name"),
        )
        incident = get_object_or_404(rows, id=incident_id)
        return _json({"incident": _serialize_incident(incident, include_timeline=True)})
    except Exception as exc:
        return _error_response(exc)
