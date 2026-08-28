from __future__ import annotations

from django.conf import settings
from django.utils import timezone

from .models import (
    HealthObservation,
    KnownGoodSnapshot,
    ManagedDomain,
    Organization,
    ProviderConnection,
)


def _check(check_id: str, label: str, *, ok: bool, required: bool, detail: str) -> dict:
    return {
        "id": check_id,
        "label": label,
        "status": "PASS" if ok else ("FAIL" if required else "WARN"),
        "required": required,
        "detail": detail,
    }


def build_demo_readiness(organization: Organization) -> dict:
    """Build a provider-free hackathon preflight from server config and local evidence.

    This function never constructs a provider client and never returns credential values.
    It answers a narrower question: is the active tenant prepared to demonstrate the
    deterministic detection -> approval -> recovery story safely in the sandbox?
    """

    managed_domains = list(
        ManagedDomain.objects.filter(
            organization=organization,
            is_active=True,
        ).order_by("name")
    )
    domain_names = [row.name for row in managed_domains]

    provider_bound = ProviderConnection.objects.filter(
        organization=organization,
        provider=ProviderConnection.Provider.NAMECOM,
        is_active=True,
    ).exists()

    exact_baselines: dict[str, KnownGoodSnapshot] = {}
    if domain_names:
        for baseline in KnownGoodSnapshot.objects.select_related("snapshot").filter(
            domain_name__in=domain_names
        ):
            if baseline.snapshot.domain_name == baseline.domain_name:
                exact_baselines[baseline.domain_name] = baseline

    primary_domain = next(
        (name for name in domain_names if name in exact_baselines),
        domain_names[0] if domain_names else None,
    )
    latest_health = (
        HealthObservation.objects.filter(domain_name=primary_domain).first()
        if primary_domain
        else None
    )

    monitor_window = max(180, int(settings.DOMAIN_MONITOR_INTERVAL_SECONDS) * 3)
    monitoring_fresh = False
    monitoring_detail = "No monitoring evidence exists for the demo domain yet."
    if latest_health is not None:
        age_seconds = max(
            0,
            int((timezone.now() - latest_health.checked_at).total_seconds()),
        )
        monitoring_fresh = age_seconds <= monitor_window
        monitoring_detail = (
            f"Latest health evidence is {age_seconds}s old; demo window is {monitor_window}s."
        )

    checks = [
        _check(
            "sandbox_environment",
            "Sandbox provider environment",
            ok=settings.NAMECOM_ENVIRONMENT == "sandbox",
            required=True,
            detail=f"Configured environment: {settings.NAMECOM_ENVIRONMENT or 'unset'}.",
        ),
        _check(
            "server_credentials",
            "Server-side name.com credentials",
            ok=bool(settings.NAMECOM_USERNAME and settings.NAMECOM_API_TOKEN),
            required=True,
            detail="Username/token are present server-side." if settings.NAMECOM_USERNAME and settings.NAMECOM_API_TOKEN else "Username and/or token are missing; values are never returned by this endpoint.",
        ),
        _check(
            "provider_binding",
            "Active tenant provider binding",
            ok=provider_bound,
            required=True,
            detail="Active name.com binding exists for this organization." if provider_bound else "Enable the tenant's name.com ProviderConnection before the demo.",
        ),
        _check(
            "managed_domain",
            "Active managed domain",
            ok=bool(managed_domains),
            required=True,
            detail=f"{len(managed_domains)} active managed domain(s) are attached to this tenant.",
        ),
        _check(
            "known_good_baseline",
            "Exact known-good baseline",
            ok=bool(exact_baselines),
            required=True,
            detail=f"{len(exact_baselines)} active domain(s) have an exact same-domain known-good chain." if exact_baselines else "Create and approve a known-good snapshot for at least one active domain.",
        ),
        _check(
            "sandbox_dns_mutations",
            "Sandbox DNS recovery armed",
            ok=bool(settings.NAMECOM_ALLOW_MUTATIONS),
            required=True,
            detail="Sandbox DNS mutation is enabled for the live recovery path." if settings.NAMECOM_ALLOW_MUTATIONS else "NAMECOM_ALLOW_MUTATIONS is disabled; preview works but the live recovery step cannot apply.",
        ),
        _check(
            "monitoring_freshness",
            "Fresh monitoring evidence",
            ok=monitoring_fresh,
            required=False,
            detail=monitoring_detail,
        ),
        _check(
            "emergency_registration",
            "Emergency registration drill armed",
            ok=bool(settings.NAMECOM_ALLOW_DOMAIN_REGISTRATION),
            required=False,
            detail="Sandbox registration is enabled." if settings.NAMECOM_ALLOW_DOMAIN_REGISTRATION else "Emergency registration remains disabled; this does not block the core recovery demo.",
        ),
    ]

    blockers = [row for row in checks if row["status"] == "FAIL"]
    warnings = [row for row in checks if row["status"] == "WARN"]

    return {
        "status": "READY" if not blockers else "BLOCKED",
        "organization": {
            "id": str(organization.id),
            "name": organization.name,
            "slug": organization.slug,
        },
        "environment": settings.NAMECOM_ENVIRONMENT,
        "primaryDomain": primary_domain,
        "managedDomainCount": len(managed_domains),
        "knownGoodDomainCount": len(exact_baselines),
        "blockerCount": len(blockers),
        "warningCount": len(warnings),
        "checks": checks,
    }
