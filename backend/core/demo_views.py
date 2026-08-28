from __future__ import annotations

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .demo_readiness import build_demo_readiness
from .tenant import TenantContextError, resolve_active_membership, tenant_error_response


@require_http_methods(["GET", "OPTIONS"])
def demo_readiness(request):
    if request.method == "OPTIONS":
        response = JsonResponse({})
        response["Cache-Control"] = "no-store"
        return response

    try:
        membership = resolve_active_membership(request)
    except TenantContextError as exc:
        return tenant_error_response(exc)

    response = JsonResponse(build_demo_readiness(membership.organization))
    response["Cache-Control"] = "no-store"
    return response
