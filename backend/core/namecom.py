from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any
from urllib import error, request

from django.conf import settings


@dataclass
class NameComAPIError(Exception):
    status_code: int
    message: str
    details: str = ""
    retryable: bool = False

    def __str__(self) -> str:
        return self.message


class NameComClient:
    BASE_URLS = {
        "sandbox": "https://api.dev.name.com",
        "production": "https://api.name.com",
    }

    def __init__(self) -> None:
        self.environment = settings.NAMECOM_ENVIRONMENT
        self.username = settings.NAMECOM_USERNAME
        self.token = settings.NAMECOM_API_TOKEN
        self.timeout = settings.NAMECOM_TIMEOUT_SECONDS
        self.allow_mutations = settings.NAMECOM_ALLOW_MUTATIONS
        self.allow_production_mutations = settings.NAMECOM_ALLOW_PRODUCTION_MUTATIONS

        if self.environment not in self.BASE_URLS:
            raise ValueError("NAMECOM_ENVIRONMENT must be 'sandbox' or 'production'.")
        if not self.username or not self.token:
            raise ValueError("NAMECOM_USERNAME and NAMECOM_API_TOKEN are required.")

        if self.environment == "sandbox" and not self.username.endswith("-test"):
            self.username = f"{self.username}-test"

    @property
    def base_url(self) -> str:
        return self.BASE_URLS[self.environment]

    def _auth_header(self) -> str:
        raw = f"{self.username}:{self.token}".encode("utf-8")
        return f"Basic {base64.b64encode(raw).decode('ascii')}"

    def _ensure_mutation_allowed(self) -> None:
        if not self.allow_mutations:
            raise NameComAPIError(
                status_code=403,
                message="name.com mutations are disabled by DomainTwin configuration.",
            )
        if self.environment == "production" and not self.allow_production_mutations:
            raise NameComAPIError(
                status_code=403,
                message="Production name.com mutations require explicit opt-in.",
            )

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        mutation: bool = False,
    ) -> dict[str, Any]:
        if mutation:
            self._ensure_mutation_allowed()

        body = None
        headers = {
            "Authorization": self._auth_header(),
            "Accept": "application/json",
            "User-Agent": "DomainTwinAI/0.1",
        }
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = request.Request(
            url=f"{self.base_url}{path}",
            data=body,
            headers=headers,
            method=method,
        )

        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                api_error = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                api_error = {}

            message = api_error.get("message") or f"name.com API returned HTTP {exc.code}."
            details = api_error.get("details") or ""
            raise NameComAPIError(
                status_code=exc.code,
                message=message,
                details=details,
                retryable=exc.code in {429, 500, 502, 503, 504},
            ) from exc
        except error.URLError as exc:
            raise NameComAPIError(
                status_code=503,
                message="Unable to reach name.com API.",
                details=str(exc.reason),
                retryable=True,
            ) from exc
        except TimeoutError as exc:
            raise NameComAPIError(
                status_code=504,
                message="name.com API request timed out.",
                retryable=True,
            ) from exc

    def hello(self) -> dict[str, Any]:
        return self._request("GET", "/core/v1/hello")

    def list_domains(self) -> dict[str, Any]:
        return self._request("GET", "/core/v1/domains")

    def get_domain(self, domain_name: str) -> dict[str, Any]:
        return self._request("GET", f"/core/v1/domains/{domain_name}")

    def list_records(self, domain_name: str) -> dict[str, Any]:
        return self._request("GET", f"/core/v1/domains/{domain_name}/records")

    def create_record(self, domain_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/core/v1/domains/{domain_name}/records",
            payload,
            mutation=True,
        )

    def update_record(
        self,
        domain_name: str,
        record_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        payload = {**payload, "id": record_id}
        return self._request(
            "PUT",
            f"/core/v1/domains/{domain_name}/records/{record_id}",
            payload,
            mutation=True,
        )

    def delete_record(self, domain_name: str, record_id: int) -> dict[str, Any]:
        return self._request(
            "DELETE",
            f"/core/v1/domains/{domain_name}/records/{record_id}",
            mutation=True,
        )
