from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.http import JsonResponse

from .tenant import TenantContextError, resolve_active_membership, tenant_error_response


VIEWER = "VIEWER"
OPERATOR = "OPERATOR"
APPROVER = "APPROVER"
ADMIN = "ADMIN"

ROLES = (VIEWER, OPERATOR, APPROVER, ADMIN)
ROLE_GROUPS = {role: f"DomainTwin {role}" for role in ROLES}
ROLE_RANK = {VIEWER: 10, OPERATOR: 20, APPROVER: 30, ADMIN: 40}

READ = "read"
EVALUATE = "evaluate"
SNAPSHOT_CREATE = "snapshot:create"
BASELINE_APPROVE = "baseline:approve"
AI_GENERATE = "ai:generate"
RECOVERY_PREVIEW = "recovery:preview"
RECOVERY_APPROVE = "recovery:approve"
RECOVERY_APPLY = "recovery:apply"
EMERGENCY_DISCOVER = "emergency:discover"
EMERGENCY_PREVIEW = "emergency:preview"
EMERGENCY_APPROVE = "emergency:approve"
EMERGENCY_APPLY = "emergency:apply"
DNS_MUTATE = "dns:mutate"
ACCESS_MANAGE = "access:manage"
UNCLASSIFIED_MUTATION = "admin:unclassified-mutation"

VIEWER_CAPABILITIES = {READ}
OPERATOR_CAPABILITIES = VIEWER_CAPABILITIES | {
    EVALUATE,
    SNAPSHOT_CREATE,
    AI_GENERATE,
    RECOVERY_PREVIEW,
    EMERGENCY_DISCOVER,
    EMERGENCY_PREVIEW,
}
APPROVER_CAPABILITIES = OPERATOR_CAPABILITIES | {
    BASELINE_APPROVE,
    RECOVERY_APPROVE,
    EMERGENCY_APPROVE,
}
ADMIN_CAPABILITIES = APPROVER_CAPABILITIES | {
    RECOVERY_APPLY,
    EMERGENCY_APPLY,
    DNS_MUTATE,
    ACCESS_MANAGE,
    UNCLASSIFIED_MUTATION,
}

ROLE_CAPABILITIES = {
    VIEWER: VIEWER_CAPABILITIES,
    OPERATOR: OPERATOR_CAPABILITIES,
    APPROVER: APPROVER_CAPABILITIES,
    ADMIN: ADMIN_CAPABILITIES,
}

PUBLIC_API_PATHS = {"/api/health/"}
PUBLIC_API_PREFIXES = ("/api/auth/",)
SAFE_METHODS = {"GET", "HEAD"}


def role_for_user(user) -> str | None:
    """Legacy P2 group role used only as bootstrap/migration input after P3-D."""
    if not getattr(user, "is_authenticated", False):
        return None
    if getattr(user, "is_superuser", False):
        return ADMIN

    names = set(user.groups.values_list("name", flat=True))
    matched = [role for role, group_name in ROLE_GROUPS.items() if group_name in names]
    if not matched:
        return VIEWER
    return max(matched, key=lambda role: ROLE_RANK[role])


def capabilities_for_role(role: str | None) -> tuple[str, ...]:
    if role is None:
        return ()
    return tuple(sorted(ROLE_CAPABILITIES.get(role, set())))


def authorization_for_user(user) -> dict:
    """Legacy P2 authorization snapshot retained for bootstrap compatibility."""
    role = role_for_user(user)
    return {
        "role": role,
        "capabilities": list(capabilities_for_role(role)),
    }


def role_for_membership(membership) -> str | None:
    if membership is None:
        return None
    if not bool(getattr(membership, "is_active", False)):
        return None
    organization = getattr(membership, "organization", None)
    if organization is None or not bool(getattr(organization, "is_active", False)):
        return None
    role = str(getattr(membership, "role", ""))
    return role if role in ROLE_CAPABILITIES else None


def authorization_for_membership(membership) -> dict:
    role = role_for_membership(membership)
    return {
        "role": role,
        "capabilities": list(capabilities_for_role(role)),
    }


def user_has_capability(user, capability: str) -> bool:
    """Legacy P2 helper retained for tests/bootstrap tooling; not used by middleware."""
    role = role_for_user(user)
    return capability in ROLE_CAPABILITIES.get(role, set())


def membership_has_capability(membership, capability: str) -> bool:
    role = role_for_membership(membership)
    return capability in ROLE_CAPABILITIES.get(role, set())


def _public_api(path: str) -> bool:
    return path in PUBLIC_API_PATHS or any(path.startswith(prefix) for prefix in PUBLIC_API_PREFIXES)


def required_capability(path: str, method: str) -> str | None:
    method = method.upper()
    if method == "OPTIONS" or not path.startswith("/api/") or _public_api(path):
        return None

    if method in SAFE_METHODS:
        if path.startswith("/api/monitor/domains/") and path.endswith("/health/"):
            return EVALUATE
        return READ

    if method == "POST":
        if path.startswith("/api/namecom/domains/") and path.endswith("/records/"):
            return DNS_MUTATE
        if path.startswith("/api/twin/domains/") and path.endswith("/snapshots/"):
            return SNAPSHOT_CREATE
        if path.startswith("/api/twin/domains/") and path.endswith("/known-good/"):
            return BASELINE_APPROVE
        if path.startswith("/api/monitor/domains/") and path.endswith("/evaluate/"):
            return EVALUATE
        if path.startswith("/api/ai/incidents/") and path.endswith("/explanation/"):
            return AI_GENERATE
        if path.startswith("/api/recovery/domains/") and path.endswith("/plans/"):
            return RECOVERY_PREVIEW
        if path.startswith("/api/recovery/plans/") and path.endswith("/approve/"):
            return RECOVERY_APPROVE
        if path.startswith("/api/recovery/plans/") and path.endswith("/apply/"):
            return RECOVERY_APPLY
        if path in {"/api/emergency/search/", "/api/emergency/check/"}:
            return EMERGENCY_DISCOVER
        if path.startswith("/api/emergency/domains/") and path.endswith("/plans/"):
            return EMERGENCY_PREVIEW
        if path.startswith("/api/emergency/plans/") and path.endswith("/approve/"):
            return EMERGENCY_APPROVE
        if path.startswith("/api/emergency/plans/") and path.endswith("/apply/"):
            return EMERGENCY_APPLY

    if method in {"PUT", "PATCH", "DELETE"} and path.startswith("/api/namecom/domains/") and "/records/" in path:
        return DNS_MUTATE

    return UNCLASSIFIED_MUTATION


def _forbidden(*, capability: str, role: str | None) -> JsonResponse:
    response = JsonResponse(
        {
            "error": {
                "message": "Insufficient DomainTwin permission.",
                "status": 403,
                "requiredCapability": capability,
                "role": role,
            }
        },
        status=403,
    )
    response["Cache-Control"] = "no-store"
    return response


class RoleAuthorizationMiddleware:
    """Enforce capabilities from the server-resolved active Membership.

    P3-D deliberately does not trust Django groups or superuser status for tenant
    authorization. Groups remain bootstrap input only. Every production private API
    request must resolve an active Membership before capability evaluation.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if getattr(settings, "DOMAIN_TWIN_TESTING", False):
            return self.get_response(request)

        capability = required_capability(request.path, request.method)
        if capability is None:
            return self.get_response(request)

        if not request.user.is_authenticated:
            response = JsonResponse(
                {"error": {"message": "Authentication required.", "status": 401}},
                status=401,
            )
            response["Cache-Control"] = "no-store"
            return response

        try:
            membership = resolve_active_membership(request)
        except TenantContextError as exc:
            return tenant_error_response(exc)

        role = role_for_membership(membership)
        request.domaintwin_membership = membership
        request.domaintwin_organization = membership.organization
        request.domaintwin_role = role
        request.domaintwin_capabilities = capabilities_for_role(role)
        if not membership_has_capability(membership, capability):
            return _forbidden(capability=capability, role=role)

        return self.get_response(request)
