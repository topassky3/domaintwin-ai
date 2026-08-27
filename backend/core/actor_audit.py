from __future__ import annotations

from typing import Any

from django.conf import settings
from django.db import transaction

from .emergency import (
    append_emergency_audit,
    apply_emergency_plan,
    approve_emergency_plan,
)
from .models import EmergencyDomainPlan, Membership, RecoveryPlan
from .rbac import role_for_membership, role_for_user
from .recovery import append_recovery_audit, apply_recovery_plan, approve_recovery_plan

RECOVERY_APPROVAL_ACTOR_EVENT = "APPROVAL_ACTOR_RECORDED"
RECOVERY_EXECUTION_ACTOR_EVENT = "EXECUTION_ACTOR_AUTHORIZED"
EMERGENCY_APPROVAL_ACTOR_EVENT = "APPROVAL_ACTOR_RECORDED"
EMERGENCY_EXECUTION_ACTOR_EVENT = "EXECUTION_ACTOR_AUTHORIZED"


def _actor_membership(user, membership=None):
    if membership is not None:
        if membership.user_id != user.pk:
            raise ValueError("Actor Membership does not belong to the authenticated user.")
        if not membership.is_active or not membership.organization.is_active:
            raise ValueError("Actor audit requires an active Membership and Organization.")
        return membership

    candidates = list(
        Membership.objects.select_related("organization")
        .filter(user=user, is_active=True, organization__is_active=True)
        .order_by("organization_id")[:2]
    )
    if len(candidates) == 1:
        return candidates[0]
    return None


def actor_snapshot(user, *, membership=None) -> dict[str, Any]:
    """Capture immutable actor evidence from the active tenant Membership."""

    if not getattr(user, "is_authenticated", False):
        if getattr(settings, "DOMAIN_TWIN_TESTING", False):
            return {"userId": None, "username": "test-system", "role": "SYSTEM"}
        raise ValueError("Actor audit requires an authenticated user.")

    resolved = _actor_membership(user, membership)
    if resolved is not None:
        role = role_for_membership(resolved)
    elif getattr(settings, "DOMAIN_TWIN_TESTING", False):
        role = role_for_user(user)
    else:
        raise ValueError("Actor audit requires an explicit active Membership context.")

    if role is None:
        raise ValueError("Actor audit requires a resolved DomainTwin Membership role.")
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
def approve_recovery_plan_as(plan: RecoveryPlan, *, user, membership=None) -> RecoveryPlan:
    actor = actor_snapshot(user, membership=membership)
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
    membership=None,
    client=None,
) -> RecoveryPlan:
    actor = actor_snapshot(user, membership=membership)
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
def approve_emergency_plan_as(plan: EmergencyDomainPlan, *, user, membership=None) -> EmergencyDomainPlan:
    actor = actor_snapshot(user, membership=membership)
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
    membership=None,
    client,
) -> EmergencyDomainPlan:
    actor = actor_snapshot(user, membership=membership)
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
