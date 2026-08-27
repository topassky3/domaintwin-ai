# P3-C — Tenant-scoped derived resources

## Goal

Close the remaining IDOR boundary after P3-B. A valid authenticated user must never be able to read, explain, approve, apply or otherwise operate on a derived DomainTwin resource owned by another active Organization merely by guessing or obtaining its integer ID.

## Ownership model

P3-B established `ManagedDomain` as the canonical Organization-owned root. P3-C deliberately keeps historical evidence fields such as `domain_name`, `source_domain_name`, snapshot fingerprints and recovery/emergency fingerprints unchanged.

Derived-resource ownership is resolved through the active Organization's active `ManagedDomain.name` registry. For objects that also reference a baseline snapshot, both the resource domain and the baseline snapshot domain must belong to the active tenant. A mismatch fails closed.

This choice has three useful properties:

1. no tenant UUID is injected into deterministic fingerprint inputs;
2. no destructive rewrite of legacy evidence is required before the September 3 hackathon deadline;
3. legacy rows remain inaccessible until their domain is explicitly attached to an Organization through the P3-B ownership command.

## Protected ID routes

P3-C tenant-scopes the pure object-ID boundaries for:

- incident detail;
- incident AI explanation generation/read;
- recovery plan detail;
- recovery approval;
- recovery apply;
- emergency-domain plan detail;
- emergency-domain approval;
- emergency-domain apply.

Domain-name routes remain protected by the P3-B `TenantDomainBoundaryMiddleware` before provider/view execution.

## Failure behavior

Cross-tenant object IDs return the same non-disclosing response as a missing object:

```json
{"error":{"message":"Resource not found.","status":404}}
```

The lookup happens before AI generation, approval handlers, recovery application, emergency registration or provider client construction.

Tenant context itself preserves P3-B semantics:

- no active membership: 403;
- ambiguous active memberships without a selection: 409;
- stale selection: clear and re-resolve;
- valid active organization: scope by its active managed domains.

## P3-C acceptance criteria

- cross-tenant incident IDs are 404;
- cross-tenant AI incident IDs are 404 before AI execution;
- cross-tenant recovery IDs are 404 before approval/apply;
- cross-tenant emergency IDs are 404 before provider/mutation execution;
- resource-domain and baseline-domain disagreement fails closed;
- same-tenant object IDs remain readable;
- no fingerprint algorithm or fingerprint input changes;
- no schema/data migration is required for the P3-C boundary;
- full P1/P2/P3 regression and frontend contracts remain green.

P3-D is intentionally separate: P2 group-derived capability authority remains active until Membership becomes the RBAC source of truth.
