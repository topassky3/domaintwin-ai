from __future__ import annotations

import json

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.http import require_http_methods


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


def _serialize_user(user) -> dict:
    return {
        "id": user.pk,
        "username": user.get_username(),
        "email": user.email,
        "isStaff": bool(user.is_staff),
        "isSuperuser": bool(user.is_superuser),
    }


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
    return _json({"authenticated": True, "user": _serialize_user(request.user)})


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
    if remember:
        request.session.set_expiry(settings.SESSION_COOKIE_AGE)
    else:
        request.session.set_expiry(0)

    return _json(
        {
            "authenticated": True,
            "remember": remember,
            "user": _serialize_user(user),
        }
    )


@require_http_methods(["POST"])
def auth_logout(request):
    logout(request)
    return _json({"authenticated": False})
