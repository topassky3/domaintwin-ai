# P7 — Demo Hardening

P7 does not add another product subsystem. It makes the existing hackathon story safe, diagnosable and reproducible before deployment.

## Demo preflight

DomainTwin exposes an authenticated, tenant-scoped `GET /api/demo/readiness/` endpoint and a matching management command:

```bash
python manage.py demo_readiness --organization <slug>
```

The preflight is intentionally provider-free. It does **not** call name.com and it never returns credential values. It evaluates server configuration plus already-persisted DomainTwin evidence.

Required checks:

1. name.com environment is `sandbox`.
2. server-side name.com username and API token are present.
3. the active Organization has an active name.com `ProviderConnection`.
4. the Organization owns at least one active `ManagedDomain`.
5. at least one active domain has an exact same-domain known-good snapshot chain.
6. sandbox DNS mutation is armed so the live recovery step can actually apply.

Non-blocking warnings:

- latest monitoring evidence is missing or older than the P5 freshness window.
- sandbox emergency-domain registration is not armed.

A required failure returns `BLOCKED`; warnings do not prevent `READY`.

## Tenant and evidence safety

Readiness uses the active server-resolved Membership/Organization. It never falls back to another tenant's domains, provider binding or known-good evidence. A `KnownGoodSnapshot` whose linked snapshot belongs to another domain is ignored and therefore cannot make the demo appear ready.

The endpoint is a private read surface and is deliberately not classified as a provider crossing. Missing provider binding is reported as a readiness failure instead of causing the P4 middleware to hide the preflight itself.

## Overview UX

The private Overview now renders the preflight before live provider cards. It shows:

- `READY` or `BLOCKED`.
- blocker and warning counts.
- every individual check and remediation detail.
- primary demo domain and environment.
- manual re-run action.
- one-click entry to the safe judge walkthrough.

## Failure containment

The `/app` route tree now has explicit Next.js loading and error boundaries.

If a route throws unexpectedly, the operator is offered three safe paths:

1. retry the current view;
2. return to Overview;
3. open the static public `/demo` walkthrough.

This avoids a framework error screen during judging and keeps the narrative available even if a live dependency is temporarily unhealthy.

## Judge-day runbook

Before presenting:

```bash
python manage.py demo_readiness --organization <slug>
python manage.py monitor_domaintwin
```

Then open `/app/overview`, confirm `Demo ready`, and keep `/demo` available as the deterministic fallback story.

Do not improvise production credentials or production mutation flags during the hackathon. The P7 preflight intentionally treats a non-sandbox provider environment as blocking.

## P7 acceptance criteria

- readiness is derived without provider/network calls;
- credential values are never serialized;
- active-tenant provider/domain/baseline state is checked explicitly;
- corrupted same-tenant baseline chains cannot satisfy readiness;
- missing provider binding is reported as a readable blocker rather than hiding the endpoint;
- sandbox mutation readiness is explicit before the live recovery demo;
- monitoring freshness and emergency registration are visible non-blocking warnings;
- Overview exposes a clear, manually refreshable preflight card;
- workspace loading/error states are explicit and recoverable;
- P7 adds no schema/data migration, queue, scheduler or new external service;
- all P1–P7 contracts, backend regressions, TypeScript and production build pass in CI.

## Deferred to P8 / post-hackathon

P7 intentionally does not choose or provision the production host, TLS termination, external database, log aggregation, alert delivery integrations, distributed tracing or secret vaulting. P8 owns deployment of the already-hardened demo surface.
