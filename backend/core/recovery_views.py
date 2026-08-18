from __future__ import annotations

import json

from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Incident, KnownGoodSnapshot, RecoveryPlan
from .namecom import NameComAPIError, NameComClient
from .recovery import (
    RecoveryError,
    apply_recovery_plan,
    approve_recovery_plan,
    create_recovery_plan,
)


def _cors(response: JsonResponse) -> JsonResponse:
    response["Access-Control-Allow-Origin"] = "http://localhost:3000"
    response["Access-Control-Allow-Headers"] = "Content-Type"
    response["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response


def _json(data: dict, status: int = 200) -> JsonResponse:
    return _cors(JsonResponse(data, status=status))


def _error_response(exc: Exception) -> JsonResponse:
    if isinstance(exc, RecoveryError):
        return _json(
            {"error": {"message": str(exc), "status": exc.status_code}},
            status=exc.status_code,
        )
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


def _parse_body(request) -> dict:
    if not request.body:
        return {}
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Request body must contain valid JSON.") from exc
    if not isinstance(payload, dict):
        raise ValueError("Request JSON must be an object.")
    return payload


def _serialize_plan(plan: RecoveryPlan, *, include_audit: bool = True) -> dict:
    payload = {
        "id": plan.id,
        "domainName": plan.domain_name,
        "status": plan.status,
        "baselineSnapshotId": plan.baseline_snapshot_id,
        "baselineVersion": plan.baseline_snapshot.version,
        "incidentId": plan.incident_id,
        "liveFingerprintBefore": plan.live_fingerprint_before,
        "targetFingerprint": plan.target_fingerprint,
        "planFingerprint": plan.plan_fingerprint,
        "operationCount": len(plan.operations),
        "operations": plan.operations,
        "operationResults": plan.operation_results,
        "verification": plan.verification,
        "requiresApproval": plan.status == RecoveryPlan.Status.PREVIEW,
        "canApply": plan.status == RecoveryPlan.Status.APPROVED,
        "approvedAt": plan.approved_at.isoformat() if plan.approved_at else None,
        "appliedAt": plan.applied_at.isoformat() if plan.applied_at else None,
        "verifiedAt": plan.verified_at.isoformat() if plan.verified_at else None,
        "createdAt": plan.created_at.isoformat(),
        "updatedAt": plan.updated_at.isoformat(),
    }
    if include_audit:
        payload["audit"] = [
            {
                "sequence": event.sequence,
                "eventType": event.event_type,
                "payload": event.payload,
                "occurredAt": event.occurred_at.isoformat(),
            }
            for event in plan.audit_events.all()
        ]
    return payload


def _current_baseline_and_incident(domain_name: str):
    incident = (
        Incident.objects.filter(domain_name=domain_name, status=Incident.Status.OPEN)
        .select_related("baseline_snapshot")
        .first()
    )
    if incident:
        return incident.baseline_snapshot, incident
    marker = get_object_or_404(
        KnownGoodSnapshot.objects.select_related("snapshot"),
        domain_name=domain_name,
    )
    return marker.snapshot, None


@csrf_exempt
@require_http_methods(["GET", "POST", "OPTIONS"])
def domain_recovery_plans(request, domain_name: str):
    if request.method == "OPTIONS":
        return _json({})
    try:
        if request.method == "GET":
            rows = RecoveryPlan.objects.filter(domain_name=domain_name).select_related(
                "baseline_snapshot",
                "incident",
            )
            return _json(
                {
                    "domainName": domain_name,
                    "plans": [_serialize_plan(row, include_audit=False) for row in rows],
                    "totalCount": rows.count(),
                }
            )

        baseline, incident = _current_baseline_and_incident(domain_name)
        client = NameComClient()
        live_payload = client.list_records(domain_name)
        live_raw = live_payload.get("records") or []
        plan, created = create_recovery_plan(
            domain_name=domain_name,
            baseline=baseline,
            live_raw_records=live_raw,
            incident=incident,
        )
        return _json(
            {
                "created": created,
                "plan": _serialize_plan(plan),
            },
            status=201 if created else 200,
        )
    except ValueError as exc:
        return _json({"error": {"message": str(exc), "status": 400}}, status=400)
    except Exception as exc:
        return _error_response(exc)


@require_http_methods(["GET", "OPTIONS"])
def recovery_plan_detail(request, plan_id: int):
    if request.method == "OPTIONS":
        return _json({})
    try:
        plan = get_object_or_404(
            RecoveryPlan.objects.select_related("baseline_snapshot", "incident"),
            id=plan_id,
        )
        return _json({"plan": _serialize_plan(plan)})
    except Exception as exc:
        return _error_response(exc)


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def recovery_plan_approve(request, plan_id: int):
    if request.method == "OPTIONS":
        return _json({})
    try:
        payload = _parse_body(request)
        if payload.get("approve") is not True:
            return _json(
                {
                    "error": {
                        "message": "Explicit approval requires JSON {\"approve\": true}.",
                        "status": 400,
                    }
                },
                status=400,
            )
        plan = get_object_or_404(
            RecoveryPlan.objects.select_related("baseline_snapshot", "incident"),
            id=plan_id,
        )
        plan = approve_recovery_plan(plan)
        return _json({"plan": _serialize_plan(plan)})
    except ValueError as exc:
        return _json({"error": {"message": str(exc), "status": 400}}, status=400)
    except Exception as exc:
        return _error_response(exc)


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def recovery_plan_apply(request, plan_id: int):
    if request.method == "OPTIONS":
        return _json({})
    try:
        plan = get_object_or_404(
            RecoveryPlan.objects.select_related("baseline_snapshot", "incident"),
            id=plan_id,
        )
        plan = apply_recovery_plan(plan)
        plan.refresh_from_db()
        status = 200
        if plan.status == RecoveryPlan.Status.PARTIAL:
            status = 207
        elif plan.status == RecoveryPlan.Status.FAILED:
            status = 502
        return _json({"plan": _serialize_plan(plan)}, status=status)
    except Exception as exc:
        return _error_response(exc)
