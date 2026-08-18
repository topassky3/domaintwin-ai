from __future__ import annotations

from typing import Any

RISK_RULE_VERSION = "1.0"

RULE_POINTS = {
    "ADDRESS_RECORD_CHANGED": 30,
    "MX_REMOVED": 30,
    "NS_MODIFIED": 35,
    "TXT_CHANGED": 5,
    "HTTP_HEALTH_FAILED": 30,
    "UNKNOWN_DESTINATION": 15,
}


def severity_for_score(score: int) -> str:
    if score >= 75:
        return "CRITICAL"
    if score >= 50:
        return "HIGH"
    if score >= 25:
        return "MEDIUM"
    return "LOW"


def _record_for_change(change: dict[str, Any]) -> dict[str, Any]:
    return change.get("after") or change.get("before") or {}


def _factor(
    *,
    rule_id: str,
    reason: str,
    state: str | None = None,
    record: dict[str, Any] | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record = record or {}
    return {
        "ruleId": rule_id,
        "points": RULE_POINTS[rule_id],
        "reason": reason,
        "state": state,
        "recordType": record.get("type"),
        "host": record.get("host"),
        "before": before,
        "after": after,
    }


def evaluate_risk(
    diff: dict[str, Any],
    *,
    http_health_failed: bool = False,
    unknown_destination: bool = False,
) -> dict[str, Any]:
    factors: list[dict[str, Any]] = []

    for change in diff.get("changes", []):
        state = str(change.get("state", "")).upper()
        if state == "UNCHANGED":
            continue

        before = change.get("before")
        after = change.get("after")
        record = _record_for_change(change)
        record_type = str(record.get("type", "")).upper()
        host = record.get("host") or "@"

        if record_type in {"A", "AAAA"}:
            factors.append(
                _factor(
                    rule_id="ADDRESS_RECORD_CHANGED",
                    reason=f"{record_type} routing record for {host} changed ({state}).",
                    state=state,
                    record=record,
                    before=before,
                    after=after,
                )
            )
        elif record_type == "MX" and state == "REMOVED":
            factors.append(
                _factor(
                    rule_id="MX_REMOVED",
                    reason=f"MX record for {host} was removed.",
                    state=state,
                    record=record,
                    before=before,
                    after=after,
                )
            )
        elif record_type == "NS" and state == "MODIFIED":
            factors.append(
                _factor(
                    rule_id="NS_MODIFIED",
                    reason=f"NS record for {host} was modified.",
                    state=state,
                    record=record,
                    before=before,
                    after=after,
                )
            )
        elif record_type == "TXT":
            factors.append(
                _factor(
                    rule_id="TXT_CHANGED",
                    reason=f"TXT record for {host} changed ({state}).",
                    state=state,
                    record=record,
                    before=before,
                    after=after,
                )
            )

    if http_health_failed:
        factors.append(
            _factor(
                rule_id="HTTP_HEALTH_FAILED",
                reason="HTTP health check failed.",
            )
        )

    if unknown_destination:
        factors.append(
            _factor(
                rule_id="UNKNOWN_DESTINATION",
                reason="DNS points to a destination that is not recognized as trusted.",
            )
        )

    factors.sort(
        key=lambda item: (
            item["ruleId"],
            item.get("recordType") or "",
            item.get("host") or "",
            item.get("state") or "",
            str(item.get("before") or ""),
            str(item.get("after") or ""),
        )
    )

    raw_score = sum(factor["points"] for factor in factors)
    score = min(raw_score, 100)

    return {
        "ruleVersion": RISK_RULE_VERSION,
        "score": score,
        "rawScore": raw_score,
        "capped": raw_score > 100,
        "severity": severity_for_score(score),
        "factorCount": len(factors),
        "factors": factors,
        "context": {
            "httpHealthFailed": http_health_failed,
            "unknownDestination": unknown_destination,
        },
    }
