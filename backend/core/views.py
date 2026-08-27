import json

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .namecom import NameComAPIError, NameComClient


ALLOWED_RECORD_FIELDS = {"type", "host", "answer", "ttl", "priority"}
SAFE_DOMAIN_FIELDS = {
    "domainName",
    "createDate",
    "expireDate",
    "autorenewEnabled",
    "locked",
    "locks",
    "transferLockExpiresAt",
    "privacyEnabled",
    "nameservers",
    "renewalPrice",
}


def _cors(response: JsonResponse) -> JsonResponse:
    response["Access-Control-Allow-Origin"] = "http://localhost:3000"
    response["Access-Control-Allow-Headers"] = "Content-Type,X-CSRFToken"
    response["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
    return response


def _json(data: dict, status: int = 200) -> JsonResponse:
    return _cors(JsonResponse(data, status=status))


def _client() -> NameComClient:
    return NameComClient()


def _error_response(exc: Exception) -> JsonResponse:
    if isinstance(exc, NameComAPIError):
        return _json(
            {
                "error": {
                    "message": exc.message,
                    "details": exc.details,
                    "status": exc.status_code,
                    "retryable": exc.retryable,
                }
            },
            status=exc.status_code if 400 <= exc.status_code <= 599 else 502,
        )
    if isinstance(exc, ValueError):
        return _json({"error": {"message": str(exc), "status": 503, "retryable": False}}, status=503)
    return _json({"error": {"message": "Unexpected DomainTwin API error.", "status": 500}}, status=500)


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


def _record_payload(request) -> dict:
    payload = _parse_body(request)
    return {key: value for key, value in payload.items() if key in ALLOWED_RECORD_FIELDS}


def _safe_domain_payload(payload: dict) -> dict:
    """Return only operational metadata required by DomainTwin's browser UI.

    name.com domain responses can contain registrant/admin/billing/tech contacts.
    Those values are not needed for continuity monitoring and must not cross the
    backend-to-browser boundary.
    """
    return {key: payload[key] for key in SAFE_DOMAIN_FIELDS if key in payload}


def health(request):
    return _json({"status": "ok", "service": "domaintwin-api"})


@require_http_methods(["GET", "OPTIONS"])
def namecom_status(request):
    if request.method == "OPTIONS":
        return _json({})
    try:
        client = _client()
        hello = client.hello()
        return _json(
            {
                "status": "connected",
                "provider": "name.com",
                "environment": client.environment,
                "apiBaseUrl": client.base_url,
                "username": hello.get("username", client.username),
                "serverTime": hello.get("serverTime"),
            }
        )
    except Exception as exc:
        return _error_response(exc)


@require_http_methods(["GET", "OPTIONS"])
def namecom_domains(request):
    if request.method == "OPTIONS":
        return _json({})
    try:
        client = _client()
        return _json({"environment": client.environment, **client.list_domains()})
    except Exception as exc:
        return _error_response(exc)


@require_http_methods(["GET", "OPTIONS"])
def namecom_domain(request, domain_name: str):
    if request.method == "OPTIONS":
        return _json({})
    try:
        client = _client()
        domain = client.get_domain(domain_name)
        return _json({"environment": client.environment, "domain": _safe_domain_payload(domain)})
    except Exception as exc:
        return _error_response(exc)


@require_http_methods(["GET", "POST", "OPTIONS"])
def namecom_records(request, domain_name: str):
    if request.method == "OPTIONS":
        return _json({})
    try:
        client = _client()
        if request.method == "GET":
            return _json({"environment": client.environment, **client.list_records(domain_name)})

        payload = _record_payload(request)
        required = {"type", "host", "answer"}
        missing = sorted(required - payload.keys())
        if missing:
            return _json(
                {"error": {"message": f"Missing required DNS fields: {', '.join(missing)}", "status": 400}},
                status=400,
            )
        record = client.create_record(domain_name, payload)
        return _json({"environment": client.environment, "record": record}, status=201)
    except Exception as exc:
        return _error_response(exc)


@require_http_methods(["PUT", "DELETE", "OPTIONS"])
def namecom_record_detail(request, domain_name: str, record_id: int):
    if request.method == "OPTIONS":
        return _json({})
    try:
        client = _client()
        if request.method == "DELETE":
            result = client.delete_record(domain_name, record_id)
            return _json({"environment": client.environment, "deleted": True, "result": result})

        payload = _record_payload(request)
        if not payload:
            return _json({"error": {"message": "No supported DNS fields supplied.", "status": 400}}, status=400)
        record = client.update_record(domain_name, record_id, payload)
        return _json({"environment": client.environment, "record": record})
    except Exception as exc:
        return _error_response(exc)
