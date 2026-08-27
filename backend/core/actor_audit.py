from __future__ import annotations

from typing import Any

from django.conf import settings
from django.db import transaction

from .emergency import (
    append_emergency_audit,
    apply_emergency_plan,
    approve_emergency_plan,
)
from .models import EmergencyDomainPlan, RecoveryPlan
from .rbac import role_for_user
from .recovery import append_recovery_audit, apply_recovery_plan, approve_recovery_plan

RECOVERY_APPROVAL_ACTOR_EVENT = "APPROVAL_ACTOR_RECORDED"
RECOVERY_EXECUTION_ACTOR_EVENT = "EXECUTION_ACTOR_AUTHORIZED"
EMERGENCY_APPROVAL_ACTOR_EVENT = "APPROVAL_ACTOR_RECORDED"
EMERGENCY_EXECUTION_ACTOR_EVENT = "EXECUTION_ACTOR_AUTHORIZED"


def actor_snapshot(user) -> dict[str, Any]:
    """Capture the minimum immutable identity evidence needed for an audit event."""

    if not getattr(user, "is_authenticated", False):
        if getattr(settings, "DOMAIN_TWIN_TESTING", False):
            # Historical deterministic endpoint tests predate P2 sessions. The
            # production-style P2 security suites explicitly disable this marker.
            return {"userId": None, "username": "test-system", "role": "SYSTEM"}
        raise ValueError("Actor audit requires an authenticated user.")
    role = role_for_user(user)
    if role is None:
        raise ValueError("Actor audit requires a resolved DomainTwin role.")
    return {
        "userId": user.pk,
        "username": user.get_username(),
        "role": role,
    }


def _event_actor(plan, event_type: str) -> dict[str, Any] | None:
    event = plan.audit_events.filter(event_type=event_type).order_by("sequence", "id").first()
    if event is None or not isinstance(event.payload, dict):
        return None
    actor = event.payload.get("actor")
    return actor if isinstance(actor, dict) else None


def recovery_actor_summary(plan: RecoveryPlan) -> dict[str, Any]:
    return {
        "approvedActor": _event_actor(plan, RECOVERY_APPROVAL_ACTOR_EVENT),
        "executionActor": _event_actor(plan, RECOVERY_EXECUTION_ACTOR_EVENT),
    }


def emergency_actor_summary(plan: EmergencyDomainPlan) -> dict[str, Any]:
    return {
        "approvedActor": _event_actor(plan, EMERGENCY_APPROVAL_ACTOR_EVENT),
        "executionActor": _event_actor(plan, EMERGENCY_EXECUTION_ACTOR_EVENT),
    }


@transaction.atomic
def approve_recovery_plan_as(plan: RecoveryPlan, *, user) -> RecoveryPlan:
    """Approve a recovery plan and append an immutable actor evidence event once."""

    actor = actor_snapshot(user)
    expected_plan_fingerprint = plan.plan_fingerprint
    result = approve_recovery_plan(plan)
    result.refresh_from_db()

    if result.plan_fingerprint != expected_plan_fingerprint:
        raise RuntimeError("Recovery plan fingerprint changed while recording approval actor evidence.")

    if result.approved_at and not result.audit_events.filter(
        event_type=RECOVERY_APPROVAL_ACTOR_EVENT
    ).exists():
        append_recovery_audit(
            result,
            RECOVERY_APPROVAL_ACTOR_EVENT,
            {
                "actor": actor,
                "approvedAt": result.approved_at.isoformat(),
                "planFingerprint": result.plan_fingerprint,
                "liveFingerprintBefore": result.live_fingerprint_before,
                "targetFingerprint": result.target_fingerprint,
            },
        )
    return result


def apply_recovery_plan_as(
    plan: RecoveryPlan,
    *,
    user,
    client=None,
) -> RecoveryPlan:
    """Record the authorized executor before crossing the recovery APPLY boundary."""

    actor = actor_snapshot(user)
    plan.refresh_from_db()
    if plan.status == RecoveryPlan.Status.APPROVED:
        append_recovery_audit(
            plan,
            RECOVERY_EXECUTION_ACTOR_EVENT,
            {
                "actor": actor,
                "planFingerprint": plan.plan_fingerprint,
                "liveFingerprintBefore": plan.live_fingerprint_before,
                "targetFingerprint": plan.target_fingerprint,
            },
        )
    return apply_recovery_plan(plan, client=client)


@transaction.atomic
def approve_emergency_plan_as(plan: EmergencyDomainPlan, *, user) -> EmergencyDomainPlan:
    """Approve emergency continuity and append immutable actor evidence once."""

    actor = actor_snapshot(user)
    expected_plan_fingerprint = plan.plan_fingerprint
    result = approve_emergency_plan(plan)
    result.refresh_from_db()

    if result.plan_fingerprint != expected_plan_fingerprint:
        raise RuntimeError("Emergency plan fingerprint changed while recording approval actor evidence.")

    if result.approved_at and not result.audit_events.filter(
        event_type=EMERGENCY_APPROVAL_ACTOR_EVENT
    ).exists():
        append_emergency_audit(
            result,
            EMERGENCY_APPROVAL_ACTOR_EVENT,
            {
                "actor": actor,
                "approvedAt": result.approved_at.isoformat(),
                "planFingerprint": result.plan_fingerprint,
                "sourceDomain": result.source_domain_name,
                "targetDomain": result.target_domain_name,
                "expectedFingerprint": result.expected_fingerprint,
            },
        )
    return result


def apply_emergency_plan_as(
    plan: EmergencyDomainPlan,
    *,
    user,
    client,
) -> EmergencyDomainPlan:
    """Record each authorized emergency execution/resume before provider mutation."""

    actor = actor_snapshot(user)
    plan.refresh_from_db()
    if plan.status in {
        EmergencyDomainPlan.Status.APPROVED,
        EmergencyDomainPlan.Status.APPLYING,
    }:
        append_emergency_audit(
            plan,
            EMERGENCY_EXECUTION_ACTOR_EVENT,
            {
                "actor": actor,
                "resume": plan.status == EmergencyDomainPlan.Status.APPLYING,
                "planFingerprint": plan.plan_fingerprint,
                "sourceDomain": plan.source_domain_name,
                "targetDomain": plan.target_domain_name,
                "expectedFingerprint": plan.expected_fingerprint,
            },
        )
    return apply_emergency_plan(plan, client=client)
