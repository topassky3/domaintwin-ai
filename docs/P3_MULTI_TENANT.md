# P3 — Multi-Tenant Core

P3 turns DomainTwin's authenticated single-workspace product into a server-enforced multi-tenant SaaS core without changing the deterministic recovery engine.

## Security invariant

Tenant A must never be able to read, mutate, recover, approve, execute, or infer Tenant B resources. Tenant identity and authorization are decided by Django; the browser is never authoritative.

The recovery invariants remain unchanged:

- fingerprints are deterministic and tenant/user/role/timestamp independent;
- AI explains deterministic evidence but does not authorize or mutate DNS;
- provider credentials stay server-side;
- approval, stale-plan protection and exact post-recovery fingerprint verification remain mandatory.

## Architecture decisions

### Organization identity

`Organization.id` is a UUID generated with Python/Django stdlib support. UUIDs are appropriate for a tenant identifier that will eventually cross API/UI boundaries and avoid exposing a simple enumerable sequence. UUIDs are defense-in-depth only; authorization must still prevent IDOR.

`Organization.slug` is unique human-readable metadata, not an authorization token.

### Membership

`Membership` is the future authority connecting a Django user to an Organization with one of the existing P2 roles:

- VIEWER
- OPERATOR
- APPROVER
- ADMIN

A unique database constraint permits at most one membership per `(organization, user)`. `is_active` supports revocation without requiring destructive deletion.

P3-A intentionally does **not** replace P2's global group-derived runtime RBAC yet. That cutover belongs to P3-D after tenant context and resource scoping exist, so the migration does not create a half-tenant-aware authorization state.

### Active organization strategy (implemented in later checkpoints)

The active tenant will be server-resolved from session state, never trusted from an arbitrary organization ID supplied by the frontend.

Planned rules:

1. Only active Membership rows are eligible.
2. With exactly one active membership, Django may resolve it automatically.
3. With multiple active memberships and no valid selected tenant, private tenant-scoped operations fail closed until one is selected.
4. Selecting a tenant validates membership server-side before storing the Organization UUID in the Django session.
5. A stale/revoked session tenant is rejected and cleared.
6. Tenant scoping happens before provider calls or sensitive object lookup.

### Domain ownership root (P3-B)

P3-B will introduce a managed-domain root owned by exactly one Organization. Existing `domain_name` strings remain evidence/data fields during migration so fingerprints and historical artifacts are not rewritten.

Current direct domain-name relationships that must be migrated/scoped are:

- `DomainSnapshot.domain_name`
- `KnownGoodSnapshot.domain_name`
- `HealthObservation.domain_name`
- `Incident.domain_name`
- `RecoveryPlan.domain_name`
- `EmergencyDomainPlan.source_domain_name`
- `EmergencyDomainPlan.target_domain_name` (candidate/registered target; source ownership determines the initiating tenant)

Current URL/query boundaries also accept domain names directly for name.com, twin/snapshot, risk, monitor, incident, recovery and emergency flows. P3-B/P3-C must resolve those names through the active Organization before calling name.com or querying derived objects.

### Derived-resource tenancy (P3-C)

Tenant ownership should be derived from a secure managed-domain root and existing FK chains where that relationship is unambiguous. We will not blindly duplicate `organization_id` into every table. A direct tenant FK will only be added where it materially improves fail-closed lookup, constraints, indexing, or historical integrity; if duplicated, database/application constraints must prevent tenant mismatch.

Object-by-ID endpoints (incident, explanation, recovery plan, emergency plan) must perform tenant-scoped lookup so cross-tenant IDs resolve as 404/non-disclosing failure.

### Existing data migration

P3-A is non-destructive and does not reassign historical DNS artifacts. `bootstrap_domaintwin_org` creates an explicit Organization and Membership rows while copying each selected user's current P2 role. It is idempotent and requires explicit usernames so it cannot silently grant access to every Django account.

P3-B will attach legacy domain data to a chosen bootstrap Organization through an explicit, reversible migration strategy before tenant enforcement becomes mandatory.

## Refined checkpoints

### P3-A — Organization foundation

- Organization UUID model
- Membership model with P2-compatible roles
- active/inactive membership state
- database uniqueness and role constraints
- Django admin visibility
- explicit idempotent bootstrap command
- regression tests
- CRLF/LF-safe static contract in CI
- no runtime RBAC cutover yet
- no DNS/recovery behavior changes

### P3-B — Tenant-scoped domain inventory + active tenant context

- introduce managed-domain ownership root
- resolve active Organization from validated session membership
- bootstrap/attach existing domain data without destructive rewrite
- tenant-scope provider domain inventory and domain-name endpoints before provider calls
- cross-tenant domain names fail closed/non-disclosing

### P3-C — Tenant-scoped derived resources

- snapshots and known-good state
- health observations
- incidents and incident events
- AI explanations
- recovery plans and audit events
- emergency plans and audit events
- all object-ID endpoints tenant scoped

### P3-D — Membership RBAC cutover

- effective role comes from active Membership
- user may have different roles in different Organizations
- P2 group roles become migration/bootstrap input only
- `/api/auth/me/` exposes active tenant and membership-derived authorization
- superuser handling remains tenant-explicit rather than becoming an accidental cross-tenant bypass

### P3-E — Tenant security regression

Explicitly prove that Tenant A cannot list, fetch, infer, approve, execute, mutate DNS for, or read actor audit from Tenant B, including manipulated IDs and domain names. Validate multiple memberships, active-tenant ambiguity, revoked membership/session handling and provider pre-denial.

## P3-A acceptance criteria

P3-A is technically implemented when:

1. migrations create Organization and Membership without altering existing DNS/recovery tables;
2. one user can hold different roles in different Organizations;
3. duplicate memberships and invalid roles are rejected by database/model choices;
4. bootstrap is explicit, atomic and idempotent and preserves current P2 role as membership data;
5. existing P2 runtime authorization remains unchanged;
6. backend regression and migration drift checks pass;
7. `npm run p3:contract` passes on CRLF and LF checkouts;
8. GitHub CI is green;
9. local verification is completed before moving to P3-B.
