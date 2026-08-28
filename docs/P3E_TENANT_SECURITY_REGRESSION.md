# P3-E — Tenant security regression

P3-E is the adversarial closure of DomainTwin's multi-tenant core. It does not add product features. It attacks the cumulative P3-A through P3-D boundary and requires every cross-tenant path to fail before provider, AI, approval or mutation work can begin.

## Security invariant

Tenant A must never be able to read, list, infer, approve, execute, mutate, or recover Tenant B resources. A valid login, ADMIN role, Django group, superuser bit, guessed domain, manipulated object ID, stale session value or corrupted derived-resource chain must not weaken that rule.

## Adversarial matrix

The dedicated production-style regression covers:

- direct cross-tenant domain reads and DNS mutation attempts;
- snapshot creation, monitoring and risk paths denied before name.com execution;
- provider portfolio filtering so Tenant B domains never enter Tenant A responses;
- snapshot IDs bound to the domain in the URL, including `diff?snapshot_id=` manipulation;
- incident IDs and AI explanation requests denied before evidence generation;
- recovery and emergency plan IDs denied before approval/apply/provider boundaries;
- recovery/emergency actor-audit payloads hidden behind the same tenant-scoped plan lookup;
- tampered active-Organization session values repaired only to a Membership the user actually owns;
- explicit non-member Organization selection returning non-disclosing failure;
- revoked Membership and inactive Organization state denying provider access immediately;
- Membership role downgrade/upgrade taking effect on the next request without re-login or group override;
- inactive `ManagedDomain` revoking both direct-domain and derived-resource access;
- active-Organization switching changing both visible data and role without cross-tenant bleed;
- corrupted `KnownGoodSnapshot -> DomainSnapshot`, `Incident -> DomainSnapshot`, `RecoveryPlan -> Incident/DomainSnapshot`, and `EmergencyDomainPlan -> DomainSnapshot` chains failing closed.

## P3-E hardening rule

Tenant ownership alone is necessary but not sufficient for deterministic recovery evidence. Derived evidence must also preserve exact same-domain chain integrity. A row whose baseline belongs to a different domain is treated as inaccessible even when both domain names happen to be owned by the same Organization.

Baseline chain validation must happen before live DNS/provider work so a corrupted relationship cannot disclose another domain's records, fingerprints, operations or audit evidence through a preview response.

## Preserved invariants

P3-E does not change any fingerprint algorithm or fingerprint input. It adds no Organization/user/role/timestamp field to deterministic evidence. It requires no schema or data migration. AI remains explanation-only. name.com credentials stay server-side. Human approval, stale-plan protection, idempotency and exact post-recovery verification remain unchanged.

## P3-E acceptance criteria

P3-E is technically complete when:

1. Tenant A cannot read or mutate a Tenant B domain, and provider factories are not called on denied paths.
2. Tenant A's domain inventory/list views cannot contain Tenant B resources or cross-domain derived rows.
3. Manipulated snapshot, incident, recovery and emergency IDs fail non-disclosing before sensitive work.
4. Cross-tenant AI generation, approval, apply, registration and DNS mutation helpers are not called.
5. Actor-audit/timeline payloads are not observable through cross-tenant IDs.
6. Tampered/stale session tenant values and non-member Organization selections cannot establish authority.
7. Membership revocation, Organization deactivation, ManagedDomain deactivation and role changes take effect on the next request.
8. Exact same-domain baseline/incident/plan chain integrity is enforced before provider calls and on list/object lookups.
9. migration drift, Django system check, full backend regression, P2/P3 contracts, TypeScript and production build pass in CI.
10. local P3-E targeted regression and contracts pass before the P3 Draft PR is eligible to leave Draft/merge.
