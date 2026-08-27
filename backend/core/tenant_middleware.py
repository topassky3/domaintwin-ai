from __future__ import annotations

from django.conf import settings
from django.http import Http404, JsonResponse

from .tenant import TenantContextError, managed_domain_for_request, tenant_error_response


DOMAIN_KWARGS = ("domain_name", "source_domain")


def _not_found() -> JsonResponse:
    response = JsonResponse(
        {"error": {"message": "Resource not found.", "status": 404}},
        status=404,
    )
    response["Cache-Control"] = "no-store"
    return response


class TenantDomainBoundaryMiddleware:
    """Resolve domain ownership from the authenticated user's active Organization.

    This boundary runs after P2 RBAC and before the view. Domain names from the URL
    are never sufficient authority to reach provider or domain-scoped application
    code.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if getattr(settings, "DOMAIN_TWIN_TESTING", False):
            return None
        if request.method == "OPTIONS" or not request.path.startswith("/api/"):
            return None
        if not getattr(request.user, "is_authenticated", False):
            return None

        domain_key = next((key for key in DOMAIN_KWARGS if key in view_kwargs), None)
        if domain_key is None:
            return None

        try:
            managed_domain, membership = managed_domain_for_request(
                request,
                view_kwargs[domain_key],
            )
        except TenantContextError as exc:
            return tenant_error_response(exc)
        except Http404:
            return _not_found()

        view_kwargs[domain_key] = managed_domain.name
        request.domaintwin_membership = membership
        request.domaintwin_organization = membership.organization
        request.domaintwin_managed_domain = managed_domain
        return None
