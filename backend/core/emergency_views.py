from __future__ import annotations

import json

from django.conf import settings
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from .actor_audit import (
    apply_emergency_plan_as,
    approve_emergency_plan_as,
    emergency_actor_summary,
)
from .emergency import (
    EmergencyDomainError,
    check_candidate,
    create_emergency_plan,
    search_candidates,
)
from .models import EmergencyDomainPlan
from .namecom import NameComAPIError, NameComClient
from .tenant import TenantContextError, tenant_error_response, tenant_scoped_queryset


def _cors(response: JsonResponse) -> JsonResponse:
    response["Access-Control-Allow-Origin"] = "http://localhost:3000"
    response["Access-Control-Allow-Headers"] = "Content-Type,X-CSRFToken"
    response["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response


def _json(data: dict, status: int = 200) -> JsonResponse:
    return _cors(JsonResponse(data, status=status))


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


def _error_response(exc: Exception) -> JsonResponse:
    if isinstance(exc, TenantContextError):
        return _cors(tenant_error_response(exc))
    if isinstance(exc, EmergencyDomainError):
        return _json({"error": {"message": str(exc), "status": exc.status_code}}, status=exc.status_code)
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
    if isinstance(exc, ValueError):
        return _json({"error": {"message": str(exc), "status": 400}}, status=400)
    return _json({"error": {"message": str(exc), "status": 500}}, status=500)


def _serialize_plan(plan: EmergencyDomainPlan, *, include_audit: bool = True) -> dict:
    payload = {
        "id": plan.id,
        "status": plan.status,
        "sourceDomain": plan.source_domain_name,
        "targetDomain": plan.target_domain_name,
        "baselineSnapshotId": plan.baseline_snapshot_id,
        "baselineVersion": plan.baseline_snapshot.version,
        "availability": plan.availability,
        "registration": plan.registration,
        "expectedFingerprint": plan.expected_fingerprint,
        "actualFingerprint": plan.actual_fingerprint or None,
        "planFingerprint": plan.plan_fingerprint,
        "operationCount": len(plan.operations),
        "operations": plan.operations,
        "operationResults": plan.operation_results,
        "verification": plan.verification,
        "requiresApproval": plan.status == EmergencyDomainPlan.Status.PREVIEW,
        "canApply": plan.status == EmergencyDomainPlan.Status.APPROVED,
        "approvedAt": plan.approved_at.isoformat() if plan.approved_at else None,
        "appliedAt": plan.applied_at.isoformat() if plan.applied_at else None,
        "verifiedAt": plan.verified_at.isoformat() if plan.verified_at else None,
        "createdAt": plan.created_at.isoformat(),
        "updatedAt": plan.updated_at.isoformat(),
        **emergency_actor_summary(plan),
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


def _tenant_plan_rows(request):
    return tenant_scoped_queryset(
        request,
        EmergencyDomainPlan.objects.select_related("baseline_snapshot"),
        domain_lookups=("source_domain_name", "baseline_snapshot__domain_name"),
    )


@require_http_methods(["GET", "OPTIONS"])
def emergency_status(request):
    if request.method == "OPTIONS":
        return _json({})
    try:
        client = NameComClient()
        registration_enabled = (
            client.environment == "sandbox"
            and bool(settings.NAMECOM_ALLOW_MUTATIONS)
            and bool(settings.NAMECOM_ALLOW_DOMAIN_REGISTRATION)
        )
        return _json(
            {
                "provider": "name.com",
                "environment": client.environment,
                "sandboxOnly": True,
                "dnsMutationsEnabled": bool(settings.NAMECOM_ALLOW_MUTATIONS),
                "registrationEnabled": registration_enabled,
                "productionRegistrationSupported": False,
            }
        )
    except Exception as exc:
        return _error_response(exc)


@require_http_methods(["POST", "OPTIONS"])
def emergency_search(request):
    if request.method == "OPTIONS":
        return _json({})
    try:
        payload = _parse_body(request)
        keyword = str(payload.get("keyword") or "")
        raw_tlds = payload.get("tldFilter")
        tlds = raw_tlds if isinstance(raw_tlds, list) else None
        client = NameComClient()
        results = search_candidates(client, keyword=keyword, tld_filter=tlds)
        return _json(
            {
                "environment": client.environment,
                "purchaseType": "registration",
                "results": results,
            }
        )
    except Exception as exc:
        return _error_response(exc)


@require_http_methods(["POST", "OPTIONS"])
def emergency_check(request):
    if request.method == "OPTIONS":
        return _json({})
    try:
        payload = _parse_body(request)
        domain_name = str(payload.get("domainName") or "")
        client = NameComClient()
        result = check_candidate(client, domain_name)
        return _json({"environment": client.environment, "result": result})
    except Exception as exc:
        return _error_response(exc)


@require_http_methods(["GET", "POST", "OPTIONS"])
def emergency_plans(request, source_domain: str):
    if request.method == "OPTIONS":
        return _json({})
    try:
        if request.method == "GET":
            rows = EmergencyDomainPlan.objects.filter(source_domain_name=source_domain).select_related(
                "baseline_snapshot"
            )
            return _json(
                {
                    "sourceDomain": source_domain,
                    "plans": [_serialize_plan(row, include_audit=False) for row in rows],
                    "totalCount": rows.count(),
                }
            )

        payload = _parse_body(request)
        target_domain = str(payload.get("targetDomain") or "")
        client = NameComClient()
        plan, created = create_emergency_plan(
            source_domain=source_domain,
            target_domain=target_domain,
            client=client,
        )
        return _json(
            {"created": created, "plan": _serialize_plan(plan)},
            status=201 if created else 200,
        )
    except Exception as exc:
        return _error_response(exc)


@require_http_methods(["GET", "OPTIONS"])
def emergency_plan_detail(request, plan_id: int):
    if request.method == "OPTIONS":
        return _json({})
    try:
        plan = get_object_or_404(_tenant_plan_rows(request), id=plan_id)
        return _json({"plan": _serialize_plan(plan)})
    except Exception as exc:
        return _error_response(exc)


@require_http_methods(["POST", "OPTIONS"])
def emergency_plan_approve(request, plan_id: int):
    if request.method == "OPTIONS":
        return _json({})
    try:
        payload = _parse_body(request)
        if payload.get("approve") is not True:
            return _json(
                {"error": {"message": 'Explicit approval requires JSON {"approve": true}.', "status": 400}},
                status=400,
            )
        plan = get_object_or_404(_tenant_plan_rows(request), id=plan_id)
        return _json({"plan": _serialize_plan(approve_emergency_plan_as(plan, user=request.user))})
    except Exception as exc:
        return _error_response(exc)


@require_http_methods(["POST", "OPTIONS"])
def emergency_plan_apply(request, plan_id: int):
    if request.method == "OPTIONS":
        return _json({})
    try:
        payload = _parse_body(request)
        plan = get_object_or_404(_tenant_plan_rows(request), id=plan_id)
        if payload.get("execute") is not True or payload.get("targetDomain") != plan.target_domain_name:
            return _json(
                {
                    "error": {
                        "message": "Execution requires execute=true and the exact targetDomain from the approved plan.",
                        "status": 400,
                    }
                },
                status=400,
            )
        client = NameComClient()
        result = apply_emergency_plan_as(plan, user=request.user, client=client)
        status = 200
        if result.status == EmergencyDomainPlan.Status.PARTIAL:
            status = 207
        elif result.status == EmergencyDomainPlan.Status.FAILED:
            status = 502
        return _json({"plan": _serialize_plan(result)}, status=status)
    except Exception as exc:
        return _error_response(exc)
