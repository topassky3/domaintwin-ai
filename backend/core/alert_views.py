from __future__ import annotations

from django.db.models import F
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .models import Incident, RecoveryPlan
from .tenant import TenantContextError, tenant_error_response, tenant_scoped_queryset


SEVERITY_RANK = {
    "LOW": 10,
    "MEDIUM": 20,
    "HIGH": 30,
    "CRITICAL": 40,
}


def _json(data: dict, status: int = 200) -> JsonResponse:
    response = JsonResponse(data, status=status)
    response["Cache-Control"] = "no-store"
    return response


def _latest_consistent_plan(incident: Incident) -> RecoveryPlan | None:
    return (
        RecoveryPlan.objects.filter(
            incident=incident,
            domain_name=incident.domain_name,
            baseline_snapshot=incident.baseline_snapshot,
            baseline_snapshot__domain_name=F("domain_name"),
        )
        .order_by("-created_at", "-id")
        .first()
    )


def _serialize_alert(incident: Incident) -> dict:
    plan = _latest_consistent_plan(incident)
    return {
        "incidentId": incident.id,
        "domainName": incident.domain_name,
        "severity": incident.severity,
        "score": incident.score,
        "factorCount": len(incident.factors),
        "openedAt": incident.opened_at.isoformat(),
        "lastSeenAt": incident.last_seen_at.isoformat(),
        "evidenceFingerprint": incident.evidence_fingerprint,
        "recommendedAction": "OPEN_RECOVERY",
        "recoveryPlan": (
            {
                "id": plan.id,
                "status": plan.status,
                "operationCount": len(plan.operations),
                "updatedAt": plan.updated_at.isoformat(),
            }
            if plan
            else None
        ),
    }


@require_http_methods(["GET", "OPTIONS"])
def active_alerts(request):
    if request.method == "OPTIONS":
        return _json({})

    try:
        rows = tenant_scoped_queryset(
            request,
            Incident.objects.select_related("baseline_snapshot").filter(
                status=Incident.Status.OPEN,
                baseline_snapshot__domain_name=F("domain_name"),
            ),
            domain_lookups=("domain_name", "baseline_snapshot__domain_name"),
        )
        incidents = list(rows)
        incidents.sort(
            key=lambda incident: (
                SEVERITY_RANK.get(str(incident.severity).upper(), 0),
                int(incident.score),
                incident.opened_at,
                incident.id,
            ),
            reverse=True,
        )
        alerts = [_serialize_alert(incident) for incident in incidents]
        highest = alerts[0]["severity"] if alerts else None
        return _json(
            {
                "activeCount": len(alerts),
                "highestSeverity": highest,
                "alerts": alerts,
            }
        )
    except TenantContextError as exc:
        return tenant_error_response(exc)
