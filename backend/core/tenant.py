from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import Http404, JsonResponse

from .models import ManagedDomain, Membership, canonical_domain_name


ACTIVE_ORGANIZATION_SESSION_KEY = "domaintwin_active_organization_id"


class TenantContextError(Exception):
    def __init__(self, message: str, *, status_code: int, code: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code


def active_memberships_for_user(user):
    if not getattr(user, "is_authenticated", False):
        return Membership.objects.none()
    return (
        Membership.objects.select_related("organization")
        .filter(
            user=user,
            is_active=True,
            organization__is_active=True,
        )
        .order_by("organization__name", "organization__slug")
    )


def resolve_active_membership(request) -> Membership:
    if not getattr(request.user, "is_authenticated", False):
        raise TenantContextError(
            "Authentication required.",
            status_code=401,
            code="authentication_required",
        )

    memberships = active_memberships_for_user(request.user)
    selected_id = request.session.get(ACTIVE_ORGANIZATION_SESSION_KEY)

    if selected_id:
        try:
            selected_uuid = uuid.UUID(str(selected_id))
            selected = memberships.filter(organization_id=selected_uuid).first()
        except (ValueError, ValidationError):
            selected = None
        if selected is not None:
            return selected
        request.session.pop(ACTIVE_ORGANIZATION_SESSION_KEY, None)

    candidates = list(memberships[:2])
    if len(candidates) == 1:
        selected = candidates[0]
        request.session[ACTIVE_ORGANIZATION_SESSION_KEY] = str(selected.organization_id)
        return selected
    if not candidates:
        raise TenantContextError(
            "No active DomainTwin organization membership is available.",
            status_code=403,
            code="no_active_membership",
        )
    raise TenantContextError(
        "Select an active DomainTwin organization before accessing tenant resources.",
        status_code=409,
        code="tenant_selection_required",
    )


def select_active_organization(request, organization_id: str) -> Membership:
    if not getattr(request.user, "is_authenticated", False):
        raise TenantContextError(
            "Authentication required.",
            status_code=401,
            code="authentication_required",
        )
    try:
        organization_uuid = uuid.UUID(str(organization_id))
    except ValueError as exc:
        raise TenantContextError(
            "organizationId must be a valid UUID.",
            status_code=400,
            code="invalid_organization_id",
        ) from exc

    membership = active_memberships_for_user(request.user).filter(
        organization_id=organization_uuid
    ).first()
    if membership is None:
        raise TenantContextError(
            "Organization is not available.",
            status_code=404,
            code="organization_not_available",
        )

    request.session[ACTIVE_ORGANIZATION_SESSION_KEY] = str(membership.organization_id)
    return membership


def membership_summary(membership: Membership) -> dict:
    organization = membership.organization
    return {
        "organizationId": str(organization.id),
        "organizationSlug": organization.slug,
        "organizationName": organization.name,
        "role": membership.role,
        "membershipActive": bool(membership.is_active),
        "organizationActive": bool(organization.is_active),
    }


def managed_domain_for_request(request, domain_name: str) -> tuple[ManagedDomain, Membership]:
    membership = resolve_active_membership(request)
    try:
        canonical_name = canonical_domain_name(domain_name)
    except ValueError as exc:
        raise Http404("Resource not found.") from exc

    managed_domain = (
        ManagedDomain.objects.select_related("organization")
        .filter(
            organization=membership.organization,
            name=canonical_name,
            is_active=True,
        )
        .first()
    )
    if managed_domain is None:
        raise Http404("Resource not found.")
    return managed_domain, membership


def tenant_scoped_queryset(request, queryset, *, domain_lookups: str | tuple[str, ...]):
    """Scope legacy/derived evidence through active ManagedDomain ownership.

    Historical evidence intentionally keeps its deterministic domain-name fields. P3-C
    therefore derives ownership from the canonical ManagedDomain registry instead of
    copying organization identifiers into fingerprinted evidence. Multiple lookups may
    be supplied so a derived row and its baseline chain must agree on tenant ownership.
    """

    # Historical deterministic endpoint tests intentionally bypass production auth/RBAC
    # and the P3-B domain middleware under this explicit test-only setting. P3-C mirrors
    # that behavior; production-style security suites disable the flag and exercise the
    # full tenant boundary.
    if getattr(settings, "DOMAIN_TWIN_TESTING", False):
        return queryset

    membership = resolve_active_membership(request)
    owned_names = ManagedDomain.objects.filter(
        organization=membership.organization,
        is_active=True,
    ).values_list("name", flat=True)
    lookups = (domain_lookups,) if isinstance(domain_lookups, str) else domain_lookups
    scoped = queryset
    for lookup in lookups:
        scoped = scoped.filter(**{f"{lookup}__in": owned_names})
    return scoped


def tenant_error_response(exc: TenantContextError) -> JsonResponse:
    response = JsonResponse(
        {
            "error": {
                "message": str(exc),
                "status": exc.status_code,
                "code": exc.code,
            }
        },
        status=exc.status_code,
    )
    response["Cache-Control"] = "no-store"
    return response
