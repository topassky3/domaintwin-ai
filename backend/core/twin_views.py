from __future__ import annotations

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import DomainSnapshot, KnownGoodSnapshot
from .namecom import NameComAPIError, NameComClient
from .twin import create_snapshot, diff_records, mark_known_good, normalize_records, snapshot_fingerprint


def _cors(response: JsonResponse) -> JsonResponse:
    response["Access-Control-Allow-Origin"] = "http://localhost:3000"
    response["Access-Control-Allow-Headers"] = "Content-Type"
    response["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response


def _json(data: dict, status: int = 200) -> JsonResponse:
    return _cors(JsonResponse(data, status=status))


def _error_response(exc: Exception) -> JsonResponse:
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


def _serialize_snapshot(snapshot: DomainSnapshot, *, known_good_id: int | None = None) -> dict:
    return {
        "id": snapshot.id,
        "domainName": snapshot.domain_name,
        "version": snapshot.version,
        "records": snapshot.records,
        "recordCount": len(snapshot.records),
        "fingerprint": snapshot.fingerprint,
        "isKnownGood": snapshot.id == known_good_id,
        "createdAt": snapshot.created_at.isoformat(),
    }


def _live_records(domain_name: str) -> list[dict]:
    payload = NameComClient().list_records(domain_name)
    records = payload.get("records") or []
    if not isinstance(records, list):
        records = list(records) if records else []
    return records


@csrf_exempt
@require_http_methods(["GET", "POST", "OPTIONS"])
def snapshots(request, domain_name: str):
    if request.method == "OPTIONS":
        return _json({})
    try:
        marker = KnownGoodSnapshot.objects.filter(domain_name=domain_name).first()
        known_good_id = marker.snapshot_id if marker else None

        if request.method == "POST":
            snapshot = create_snapshot(domain_name, _live_records(domain_name))
            return _json(
                {"snapshot": _serialize_snapshot(snapshot, known_good_id=known_good_id)},
                status=201,
            )

        rows = DomainSnapshot.objects.filter(domain_name=domain_name)
        return _json(
            {
                "domainName": domain_name,
                "knownGoodSnapshotId": known_good_id,
                "snapshots": [
                    _serialize_snapshot(snapshot, known_good_id=known_good_id)
                    for snapshot in rows
                ],
                "totalCount": rows.count(),
            }
        )
    except Exception as exc:
        return _error_response(exc)


@require_http_methods(["GET", "OPTIONS"])
def snapshot_detail(request, domain_name: str, snapshot_id: int):
    if request.method == "OPTIONS":
        return _json({})
    snapshot = get_object_or_404(DomainSnapshot, id=snapshot_id, domain_name=domain_name)
    marker = KnownGoodSnapshot.objects.filter(domain_name=domain_name).first()
    return _json(
        {
            "snapshot": _serialize_snapshot(
                snapshot,
                known_good_id=marker.snapshot_id if marker else None,
            )
        }
    )


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def snapshot_known_good(request, domain_name: str, snapshot_id: int):
    if request.method == "OPTIONS":
        return _json({})
    snapshot = get_object_or_404(DomainSnapshot, id=snapshot_id, domain_name=domain_name)
    marker = mark_known_good(snapshot)
    return _json(
        {
            "domainName": domain_name,
            "knownGoodSnapshotId": marker.snapshot_id,
            "markedAt": marker.marked_at.isoformat(),
        }
    )


@require_http_methods(["GET", "OPTIONS"])
def live_diff(request, domain_name: str):
    if request.method == "OPTIONS":
        return _json({})
    try:
        snapshot_id = request.GET.get("snapshot_id")
        if snapshot_id:
            baseline = get_object_or_404(
                DomainSnapshot,
                id=int(snapshot_id),
                domain_name=domain_name,
            )
        else:
            marker = get_object_or_404(KnownGoodSnapshot, domain_name=domain_name)
            baseline = marker.snapshot

        live = normalize_records(_live_records(domain_name))
        diff = diff_records(baseline.records, live)
        return _json(
            {
                "domainName": domain_name,
                "baselineSnapshotId": baseline.id,
                "baselineVersion": baseline.version,
                "baselineFingerprint": baseline.fingerprint,
                "liveFingerprint": snapshot_fingerprint(live),
                "driftDetected": any(
                    diff["summary"][state] > 0
                    for state in ("ADDED", "REMOVED", "MODIFIED")
                ),
                **diff,
            }
        )
    except ValueError:
        return _json(
            {"error": {"message": "snapshot_id must be an integer.", "status": 400}},
            status=400,
        )
    except Exception as exc:
        return _error_response(exc)
