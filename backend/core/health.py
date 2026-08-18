from __future__ import annotations

import ipaddress
import re
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from django.conf import settings

_HOST_RE = re.compile(
    r"^(?=.{1,253}\.?$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.?$",
    re.IGNORECASE,
)


class UnsafeHealthTarget(ValueError):
    pass


@dataclass(frozen=True)
class ResolutionResult:
    ok: bool
    addresses: tuple[str, ...]
    error: str | None = None


def normalize_health_host(domain_name: str) -> str:
    host = domain_name.strip().lower().rstrip(".")
    if not host or "://" in host or "/" in host or ":" in host:
        raise UnsafeHealthTarget("Health target must be a bare public domain name.")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise UnsafeHealthTarget("Direct IP health targets are not allowed.")
    if host == "localhost" or host.endswith(".localhost") or not _HOST_RE.fullmatch(host):
        raise UnsafeHealthTarget("Health target must be a valid public domain name.")
    return host


def resolve_public_host(domain_name: str) -> ResolutionResult:
    host = normalize_health_host(domain_name)
    try:
        infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        return ResolutionResult(ok=False, addresses=(), error=f"DNS resolution failed: {exc}")

    addresses = sorted({str(info[4][0]).split("%")[0] for info in infos})
    if not addresses:
        return ResolutionResult(ok=False, addresses=(), error="DNS resolution returned no addresses.")

    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise UnsafeHealthTarget(
                f"Health target resolves to a non-public address ({address}); request blocked."
            )

    return ResolutionResult(ok=True, addresses=tuple(addresses))


def _probe_url(url: str, timeout: float) -> dict[str, Any]:
    headers = {"User-Agent": "DomainTwin-Health/1.0"}

    def execute(method: str) -> dict[str, Any]:
        request = urllib.request.Request(url, headers=headers, method=method)
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                status = int(response.getcode() or 0)
                final_url = response.geturl()
                latency_ms = round((time.perf_counter() - started) * 1000, 2)
                return {
                    "ok": 200 <= status < 400,
                    "statusCode": status,
                    "latencyMs": latency_ms,
                    "finalUrl": final_url,
                    "error": None if 200 <= status < 400 else f"Unexpected HTTP status {status}.",
                }
        except urllib.error.HTTPError as exc:
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            if method == "HEAD" and exc.code in {405, 501}:
                return {"retryWithGet": True}
            return {
                "ok": False,
                "statusCode": int(exc.code),
                "latencyMs": latency_ms,
                "finalUrl": exc.geturl() or url,
                "error": f"HTTP status {exc.code}.",
            }
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            reason = getattr(exc, "reason", exc)
            return {
                "ok": False,
                "statusCode": None,
                "latencyMs": latency_ms,
                "finalUrl": url,
                "error": str(reason),
            }

    result = execute("HEAD")
    if result.get("retryWithGet"):
        result = execute("GET")
    return result


def check_domain_health(domain_name: str) -> dict[str, Any]:
    host = normalize_health_host(domain_name)
    resolution = resolve_public_host(host)
    timeout = float(getattr(settings, "DOMAIN_HEALTH_TIMEOUT_SECONDS", 4.0))

    if not resolution.ok:
        failed_probe = {
            "ok": False,
            "statusCode": None,
            "latencyMs": 0.0,
            "finalUrl": None,
            "error": resolution.error,
        }
        http_probe = {**failed_probe, "url": f"http://{host}/"}
        https_probe = {**failed_probe, "url": f"https://{host}/"}
    else:
        http_probe = {"url": f"http://{host}/", **_probe_url(f"http://{host}/", timeout)}
        https_probe = {"url": f"https://{host}/", **_probe_url(f"https://{host}/", timeout)}

    availability_ok = bool(http_probe["ok"] or https_probe["ok"])
    return {
        "domainName": host,
        "dnsResolution": {
            "ok": resolution.ok,
            "addresses": list(resolution.addresses),
            "error": resolution.error,
        },
        "http": http_probe,
        "https": https_probe,
        "availabilityOk": availability_ok,
        "availabilityFailed": not availability_ok,
    }
