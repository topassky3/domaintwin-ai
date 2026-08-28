from __future__ import annotations

from django.conf import settings
from django.http import JsonResponse

from .models import ProviderConnection
from .tenant import TenantContextError, resolve_active_membership, tenant_error_response


NAMECOM = ProviderConnection.Provider.NAMECOM


def requires_namecom_provider(path: str, method: str) -> bool:
    """Return whether this request can cross the name.com provider boundary."""

    method = method.upper()
    if method == "OPTIONS" or not path.startswith("/api/"):
        return False

    if path.startswith("/api/namecom/"):
        return True

    if path.startswith("/api/twin/domains/"):
        if method == "POST" and path.endswith("/snapshots/"):
            return True
        if method == "GET" and path.endswith("/diff/"):
            return True

    if method == "GET" and path.startswith("/api/risk/domains/"):
        return True

    if (
        method == "POST"
        and path.startswith("/api/monitor/domains/")
        and path.endswith("/evaluate/")
    ):
        return True

    if (
        method == "POST"
        and path.startswith("/api/recovery/domains/")
        and path.endswith("/plans/")
    ):
        return True
    if (
        method == "POST"
        and path.startswith("/api/recovery/plans/")
        and path.endswith("/apply/")
    ):
        return True

    if path == "/api/emergency/status/" and method == "GET":
        return True
    if path in {"/api/emergency/search/", "/api/emergency/check/"} and method == "POST":
        return True
    if (
        method == "POST"
        and path.startswith("/api/emergency/domains/")
        and path.endswith("/plans/")
    ):
        return True
    if (
        method == "POST"
        and path.startswith("/api/emergency/plans/")
        and path.endswith("/apply/")
    ):
        return True

    return False


def provider_connection_required_response() -> JsonResponse:
    response = JsonResponse(
        {
            "error": {
                "message": "name.com is not enabled for the active DomainTwin organization.",
                "status": 409,
                "code": "provider_connection_required",
                "provider": NAMECOM,
            }
        },
        status=409,
    )
    response["Cache-Control"] = "no-store"
    return response


class ProviderConnectionBoundaryMiddleware:
    """Fail closed before provider code when the active tenant lacks a binding.

    P4 intentionally stores no provider username, token, password or secret in the
    database. ProviderConnection is only the tenant authorization binding; the actual
    name.com credential continues to live exclusively in backend environment settings.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if getattr(settings, "DOMAIN_TWIN_TESTING", False):
            return None
        if not requires_namecom_provider(request.path, request.method):
            return None
        if not getattr(request.user, "is_authenticated", False):
            return None

        membership = getattr(request, "domaintwin_membership", None)
        if membership is None:
            try:
                membership = resolve_active_membership(request)
            except TenantContextError as exc:
                return tenant_error_response(exc)

        connection = (
            ProviderConnection.objects.select_related("organization")
            .filter(
                organization=membership.organization,
                provider=NAMECOM,
                is_active=True,
            )
            .first()
        )
        if connection is None:
            return provider_connection_required_response()

        request.domaintwin_provider_connection = connection
        return None
