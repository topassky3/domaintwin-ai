from __future__ import annotations

import json

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.http import require_http_methods

from .rbac import authorization_for_membership
from .tenant import (
    ACTIVE_ORGANIZATION_SESSION_KEY,
    TenantContextError,
    active_memberships_for_user,
    membership_summary,
    resolve_active_membership,
    select_active_organization,
    tenant_error_response,
)


def _json(data: dict, status: int = 200) -> JsonResponse:
    response = JsonResponse(data, status=status)
    response["Cache-Control"] = "no-store"
    return response


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


def _serialize_user(user, membership=None) -> dict:
    authorization = authorization_for_membership(membership)
    return {
        "id": user.pk,
        "username": user.get_username(),
        "email": user.email,
        "isStaff": bool(user.is_staff),
        "isSuperuser": bool(user.is_superuser),
        **authorization,
    }


def _session_tenant_state(request):
    try:
        membership = resolve_active_membership(request)
        return membership, False, None
    except TenantContextError as exc:
        if exc.code == "tenant_selection_required":
            return None, True, exc.code
        if exc.code == "no_active_membership":
            return None, False, exc.code
        raise


def _authenticated_payload(request, user, *, remember: bool | None = None) -> dict:
    membership, selection_required, tenant_error_code = _session_tenant_state(request)
    payload = {
        "authenticated": True,
        "user": _serialize_user(user, membership),
        "activeOrganization": membership_summary(membership) if membership else None,
        "selectionRequired": selection_required,
        "tenantErrorCode": tenant_error_code,
    }
    if remember is not None:
        payload["remember"] = remember
    return payload


def _resolve_login_user(identifier: str):
    User = get_user_model()
    manager = User._default_manager
    username_field = User.USERNAME_FIELD

    by_username = manager.filter(**{f"{username_field}__iexact": identifier}).first()
    if by_username is not None:
        return by_username

    if hasattr(User, "email"):
        matches = list(manager.filter(email__iexact=identifier)[:2])
        if len(matches) == 1:
            return matches[0]

    return None


@require_http_methods(["GET"])
def auth_csrf(request):
    return _json({"csrfToken": get_token(request)})


@require_http_methods(["GET"])
def auth_me(request):
    if not request.user.is_authenticated:
        return _json(
            {"error": {"message": "Authentication required.", "status": 401}},
            status=401,
        )
    try:
        return _json(_authenticated_payload(request, request.user))
    except TenantContextError as exc:
        return tenant_error_response(exc)


@require_http_methods(["GET"])
def auth_organizations(request):
    if not request.user.is_authenticated:
        return _json(
            {"error": {"message": "Authentication required.", "status": 401}},
            status=401,
        )

    memberships = list(active_memberships_for_user(request.user))
    active = None
    selection_required = False
    try:
        active = resolve_active_membership(request)
    except TenantContextError as exc:
        if exc.code == "tenant_selection_required":
            selection_required = True
        elif exc.code != "no_active_membership":
            return tenant_error_response(exc)

    return _json(
        {
            "organizations": [membership_summary(row) for row in memberships],
            "activeOrganization": membership_summary(active) if active else None,
            "selectionRequired": selection_required,
        }
    )


@require_http_methods(["POST"])
def auth_active_organization(request):
    if not request.user.is_authenticated:
        return _json(
            {"error": {"message": "Authentication required.", "status": 401}},
            status=401,
        )

    try:
        payload = _parse_body(request)
    except ValueError as exc:
        return _json({"error": {"message": str(exc), "status": 400}}, status=400)

    organization_id = str(payload.get("organizationId") or "").strip()
    if not organization_id:
        return _json(
            {"error": {"message": "organizationId is required.", "status": 400}},
            status=400,
        )

    try:
        membership = select_active_organization(request, organization_id)
    except TenantContextError as exc:
        return tenant_error_response(exc)

    return _json(
        {
            "activeOrganization": membership_summary(membership),
            "authorization": authorization_for_membership(membership),
        }
    )


@require_http_methods(["POST"])
def auth_login(request):
    try:
        payload = _parse_body(request)
    except ValueError as exc:
        return _json({"error": {"message": str(exc), "status": 400}}, status=400)

    identifier = str(payload.get("identifier") or "").strip()
    password = str(payload.get("password") or "")
    remember = payload.get("remember") is True

    if not identifier or not password:
        return _json(
            {"error": {"message": "Identifier and password are required.", "status": 400}},
            status=400,
        )

    candidate = _resolve_login_user(identifier)
    if candidate is None:
        return _json(
            {"error": {"message": "Invalid credentials.", "status": 401}},
            status=401,
        )

    user = authenticate(
        request=request,
        username=candidate.get_username(),
        password=password,
    )
    if user is None:
        return _json(
            {"error": {"message": "Invalid credentials.", "status": 401}},
            status=401,
        )

    login(request, user)
    request.session.pop(ACTIVE_ORGANIZATION_SESSION_KEY, None)
    if remember:
        request.session.set_expiry(settings.SESSION_COOKIE_AGE)
    else:
        request.session.set_expiry(0)

    try:
        return _json(_authenticated_payload(request, user, remember=remember))
    except TenantContextError as exc:
        return tenant_error_response(exc)


@require_http_methods(["POST"])
def auth_logout(request):
    logout(request)
    return _json({"authenticated": False})
