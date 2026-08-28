from __future__ import annotations

from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from .models import KnownGoodSnapshot
from .namecom import NameComAPIError, NameComClient
from .risk import evaluate_risk
from .tenant import require_snapshot_domain
from .twin import diff_records, normalize_records, snapshot_fingerprint


def _cors(response: JsonResponse) -> JsonResponse:
    response["Access-Control-Allow-Origin"] = "http://localhost:3000"
    response["Access-Control-Allow-Headers"] = "Content-Type"
    response["Access-Control-Allow-Methods"] = "GET,OPTIONS"
    return response


def _json(data: dict, status: int = 200) -> JsonResponse:
    return _cors(JsonResponse(data, status=status))


def _error_response(exc: Exception) -> JsonResponse:
    if isinstance(exc, Http404):
        return _json(
            {"error": {"message": "Known-good snapshot not found.", "status": 404}},
            status=404,
        )
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


def _parse_bool(value: str | None, *, field: str) -> bool:
    if value is None:
        return False
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes"}:
        return True
    if normalized in {"0", "false", "no"}:
        return False
    raise ValueError(f"{field} must be one of 1/0, true/false, or yes/no.")


def _live_records(domain_name: str) -> list[dict]:
    payload = NameComClient().list_records(domain_name)
    records = payload.get("records") or []
    if not isinstance(records, list):
        records = list(records) if records else []
    return records


@require_http_methods(["GET", "OPTIONS"])
def domain_risk(request, domain_name: str):
    if request.method == "OPTIONS":
        return _json({})

    try:
        http_health_failed = _parse_bool(
            request.GET.get("http_health_failed"),
            field="http_health_failed",
        )
        unknown_destination = _parse_bool(
            request.GET.get("unknown_destination"),
            field="unknown_destination",
        )

        marker = get_object_or_404(
            KnownGoodSnapshot.objects.select_related("snapshot"),
            domain_name=domain_name,
        )
        baseline = require_snapshot_domain(marker.snapshot, domain_name)
        live = normalize_records(_live_records(domain_name))
        diff = diff_records(baseline.records, live)

        risk = evaluate_risk(
            diff,
            http_health_failed=http_health_failed,
            unknown_destination=unknown_destination,
        )
        drift_detected = any(
            diff["summary"][state] > 0
            for state in ("ADDED", "REMOVED", "MODIFIED")
        )

        return _json(
            {
                "domainName": domain_name,
                "baselineSnapshotId": baseline.id,
                "baselineVersion": baseline.version,
                "baselineFingerprint": baseline.fingerprint,
                "liveFingerprint": snapshot_fingerprint(live),
                "driftDetected": drift_detected,
                "diffSummary": diff["summary"],
                "risk": risk,
            }
        )
    except ValueError as exc:
        return _json(
            {"error": {"message": str(exc), "status": 400}},
            status=400,
        )
    except Exception as exc:
        return _error_response(exc)
