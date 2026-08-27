from __future__ import annotations

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from .ai import build_evidence_bundle, generate_incident_explanation, resolve_evidence
from .models import Incident, IncidentExplanation


def _cors(response: JsonResponse) -> JsonResponse:
    response["Access-Control-Allow-Origin"] = "http://localhost:3000"
    response["Access-Control-Allow-Headers"] = "Content-Type,X-CSRFToken"
    response["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response


def _json(data: dict, status: int = 200) -> JsonResponse:
    return _cors(JsonResponse(data, status=status))


def _serialize(explanation: IncidentExplanation, *, cached: bool) -> dict:
    analysis = explanation.analysis or {}
    return {
        "label": "Evidence-based AI analysis",
        "status": explanation.status,
        "aiAvailable": explanation.status == IncidentExplanation.Status.GENERATED,
        "cached": cached,
        "explanationId": explanation.id,
        "incidentId": explanation.incident_id,
        "evidenceFingerprint": explanation.evidence_fingerprint,
        "provider": explanation.provider,
        "model": explanation.model,
        "probableCause": analysis.get("probable_cause"),
        "affectedService": analysis.get("affected_service"),
        "evidenceRefs": analysis.get("evidence_refs") or [],
        "evidence": resolve_evidence(explanation),
        "recommendedAction": analysis.get("recommended_action"),
        "confidence": analysis.get("confidence") or {},
        "requestId": explanation.request_id or None,
        "latencyMs": explanation.latency_ms,
        "error": explanation.error_message or None,
        "generatedAt": explanation.updated_at.isoformat(),
        "safety": {
            "factsComeFromDeterministicEvidence": True,
            "aiCanMutateDns": False,
            "humanApprovalStillRequired": True,
        },
    }


@require_http_methods(["GET", "POST", "OPTIONS"])
def incident_explanation(request, incident_id: int):
    if request.method == "OPTIONS":
        return _json({})

    incident = get_object_or_404(
        Incident.objects.select_related("baseline_snapshot"),
        id=incident_id,
    )

    if request.method == "GET":
        latest = IncidentExplanation.objects.filter(
            incident=incident,
            evidence_fingerprint=incident.evidence_fingerprint,
        ).first()
        if latest:
            return _json({"analysis": _serialize(latest, cached=True)})

        bundle, catalog = build_evidence_bundle(incident)
        return _json(
            {
                "analysis": {
                    "label": "Evidence-based AI analysis",
                    "status": "NOT_GENERATED",
                    "aiAvailable": False,
                    "cached": False,
                    "explanationId": None,
                    "incidentId": incident.id,
                    "evidenceFingerprint": incident.evidence_fingerprint,
                    "evidence": catalog,
                    "probableCause": None,
                    "affectedService": None,
                    "recommendedAction": None,
                    "confidence": {},
                    "inputContract": {
                        "previous_state": bundle["previous_state"],
                        "current_state": bundle["current_state"],
                        "dns_diff": bundle["dns_diff"],
                        "health_checks": bundle["health_checks"],
                        "risk_score": bundle["risk_score"],
                        "timestamps": bundle["timestamps"],
                    },
                    "safety": {
                        "factsComeFromDeterministicEvidence": True,
                        "aiCanMutateDns": False,
                        "humanApprovalStillRequired": True,
                    },
                }
            }
        )

    force = request.GET.get("force", "0").strip().lower() in {"1", "true", "yes"}
    explanation, cached = generate_incident_explanation(incident, force=force)
    return _json({"analysis": _serialize(explanation, cached=cached)})
