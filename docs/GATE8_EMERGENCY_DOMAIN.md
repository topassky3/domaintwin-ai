# Gate 8 — Emergency Domain Continuity

## Goal

Gate 8 adds a second sponsor-facing WOW flow to DomainTwin:

`SEARCH -> CHECK -> PREVIEW -> APPROVE -> REGISTER -> CLONE -> VERIFY -> READY`

The operator can discover a standard emergency domain through name.com, re-check its exact availability, preview the known-good DNS clone without mutation, explicitly approve the action, register the target in the name.com sandbox, clone the protected source domain's trusted DNS, and prove the resulting live fingerprint matches the source known-good snapshot.

## Product route

- `/app/emergency`

The route is also present in the permanent product navigation and linked from Overview.

## Backend endpoints

- `GET /api/emergency/status/`
- `POST /api/emergency/search/`
- `POST /api/emergency/check/`
- `GET|POST /api/emergency/domains/{sourceDomain}/plans/`
- `GET /api/emergency/plans/{planId}/`
- `POST /api/emergency/plans/{planId}/approve/`
- `POST /api/emergency/plans/{planId}/apply/`

The browser still uses the Gate 7 same-origin `/api/domaintwin/*` proxy. name.com credentials never enter client-side code.

## name.com Core integration

Gate 8 intentionally follows the simple standard-registration path:

- Search: `POST /core/v1/domains:search`
- Exact pre-registration check: `POST /core/v1/domains:checkAvailability`
- Register: `POST /core/v1/domains`
- Read DNS: `GET /core/v1/domains/{domainName}/records`
- Clone DNS: `POST /core/v1/domains/{domainName}/records`

Search and Check use `purchaseType=registration`. The literal `:` in the first two endpoint paths must not be URL-encoded. Domain registration uses `X-Idempotency-Key` and the same persisted key is reused when an `APPLYING` plan resumes after a transient registration timeout.

## Deliberate MVP scope

Gate 8 only accepts:

- standard `purchaseType=registration` inventory;
- non-premium domains;
- ASCII `.com`, `.net`, and `.org` targets.

Premium, aftermarket, expiring, backorder, claims-period, IDN and TLD-specific-requirement flows are excluded from this hackathon gate instead of being silently handled incorrectly.

## Safety invariants

1. Search and exact availability checks are read-only.
2. Preview creation is read-only.
3. DNS mutation permission alone is insufficient for registration.
4. Registration requires `NAMECOM_ALLOW_DOMAIN_REGISTRATION=1` in addition to `NAMECOM_ALLOW_MUTATIONS=1`.
5. Gate 8 registration is hard-blocked outside `sandbox`.
6. Approval requires exact JSON `{ "approve": true }`.
7. Apply requires `execute=true` and the exact `targetDomain` stored in the approved plan.
8. Create Domain sends a persisted `X-Idempotency-Key`.
9. After registration, DomainTwin reads the target's real DNS before cloning.
10. If reconciliation would require an unpreviewed `UPDATE` or `DELETE`, cloning aborts instead of making that mutation.
11. Target DNS is read again after clone.
12. `READY` is persisted only if target live fingerprint equals the source known-good fingerprint exactly.
13. Provider contact data is not persisted or returned by the emergency-plan API.
14. Audit history is persistent and inspectable.

## Expected happy-path audit

With a one-record source snapshot, the clean happy path should contain:

1. `PLAN_CREATED`
2. `PLAN_APPROVED`
3. `REGISTRATION_STARTED`
4. `DOMAIN_REGISTERED`
5. `CLONE_STARTED`
6. `DNS_RECORD_CLONED`
7. `CLONE_VERIFIED`
8. `EMERGENCY_DOMAIN_READY`

If a registration request times out before its response is persisted, a retry may additionally contain `APPLY_RESUMED` and `REGISTRATION_RETRY`; it reuses the same provider idempotency key.

## Safe local smoke — no registration

Keep the backend in sandbox and all mutation switches off:

```text
NAMECOM_ENVIRONMENT=sandbox
NAMECOM_ALLOW_MUTATIONS=0
NAMECOM_ALLOW_PRODUCTION_MUTATIONS=0
NAMECOM_ALLOW_DOMAIN_REGISTRATION=0
AI_PROVIDER=disabled
```

Safe smoke acceptance:

- `/app/emergency` loads with `SANDBOX` and registration blocked;
- real name.com Search returns candidates/prices;
- a standard non-premium candidate can be selected;
- exact Check returns current availability;
- an emergency PREVIEW can be created from the source known-good snapshot;
- preview operations and expected fingerprint are visible;
- no registration or DNS mutation occurs.

## Controlled sandbox Golden Drill

Only after safe smoke passes, restart Django with:

```text
NAMECOM_ENVIRONMENT=sandbox
NAMECOM_ALLOW_MUTATIONS=1
NAMECOM_ALLOW_PRODUCTION_MUTATIONS=0
NAMECOM_ALLOW_DOMAIN_REGISTRATION=1
AI_PROVIDER=disabled
```

Then perform through the browser:

1. Search.
2. Select a standard non-premium candidate.
3. Check exact availability.
4. Create preview.
5. Verify source, target, snapshot, price, operations and expected fingerprint.
6. Approve.
7. Verify the UI is visibly SANDBOX and registration is armed.
8. Execute `Register + clone + verify`.
9. Confirm plan `READY`.
10. Confirm `EXPECTED == ACTUAL` and `MATCH YES`.
11. Confirm ordered audit.
12. Confirm target appears in name.com domains.

## Mandatory reset after Golden Drill

Immediately return to:

```text
NAMECOM_ALLOW_MUTATIONS=0
NAMECOM_ALLOW_PRODUCTION_MUTATIONS=0
NAMECOM_ALLOW_DOMAIN_REGISTRATION=0
AI_PROVIDER=disabled
```

Restart Django and verify the effective settings before final regression.

## Local quality gates

Backend:

```text
python manage.py makemigrations --check
python manage.py migrate
python manage.py check
python manage.py test core
```

Frontend:

```text
npm run gate7:contract
npm run gate8:contract
npm run typecheck
npm run build
```

Before merge, generated build artifacts must be cleaned and `git status --short` must return no output.

## Merge acceptance

Gate 8 can merge only after:

- backend migrations/check/tests pass;
- Gate 7 regression contract still passes;
- Gate 8 contract passes;
- TypeScript and production build pass;
- safe smoke is visually verified;
- controlled sandbox Golden Drill reaches `READY` + `MATCH YES`;
- runtime is reset to safe defaults;
- final regression passes;
- working tree is clean.
