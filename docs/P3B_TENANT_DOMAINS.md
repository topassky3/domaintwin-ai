# P3-B — Tenant-scoped domain inventory and active tenant context

P3-B establishes the first runtime tenant boundary in DomainTwin. P2 group RBAC remains the effective capability source until P3-D; this checkpoint only decides **which Organization and domains a request is allowed to address**.

## Security boundary

A browser-supplied domain name is never authority. For every domain-name endpoint, Django resolves the active Organization from a validated active `Membership`, then resolves the requested name through `ManagedDomain` before the view executes.

The order is:

1. Django session authentication.
2. P2 capability/RBAC enforcement.
3. Active Organization resolution from server-side Membership state.
4. Managed-domain ownership lookup inside that Organization.
5. Only then may the view query historical state or instantiate/call name.com.

A domain owned by another Organization returns a non-disclosing 404 and provider code is not reached.

## Active Organization session rules

The selected tenant is stored in the Django session under `domaintwin_active_organization_id`.

- one active membership: auto-select it;
- multiple active memberships with no valid selection: fail closed with 409 until explicitly selected;
- zero active memberships: fail closed with 403;
- stale, inactive, deleted or revoked session membership: clear it and re-resolve;
- explicit selection accepts only an Organization for which the current user has an active Membership and whose Organization is active.

`GET /api/auth/organizations/` exposes only the authenticated user's eligible organizations. `POST /api/auth/active-organization/` validates membership server-side before changing session context.

## ManagedDomain ownership root

`ManagedDomain` is an Organization-owned UUID root with a globally unique canonical domain name. Global uniqueness makes ownership unambiguous during the current shared-provider-account architecture. Domain names are normalized to lowercase with a trailing dot removed before persistence.

Existing snapshot, health, incident, recovery and emergency evidence is **not rewritten in P3-B**. Those tables remain unchanged until P3-C attaches/derives their tenant ownership.

## Legacy attachment

`attach_domaintwin_domains` creates ownership roots without changing historical evidence:

```text
python manage.py attach_domaintwin_domains <organization-slug> --domain example.com
python manage.py attach_domaintwin_domains <organization-slug> --from-legacy
```

The command preflights cross-Organization ownership conflicts and is safe to re-run. `--detach` removes only matching `ManagedDomain` roots, making the P3-B mapping reversible before P3-C introduces derived-resource relationships.

## Provider inventory

`GET /api/namecom/domains/` resolves the active Organization first and returns only provider domains that are present as active `ManagedDomain` rows for that Organization. If the tenant owns no managed domains, the endpoint returns an empty list without calling the provider.

## P3-B acceptance criteria

P3-B is technically implemented when:

1. `ManagedDomain` gives each managed name exactly one Organization owner;
2. active Organization selection is derived only from active server-side Membership state;
3. one membership auto-selects, multiple memberships fail closed until selection, and stale selections are cleared;
4. every URL carrying `domain_name` or emergency `source_domain` is ownership-gated before its view/provider code;
5. a cross-tenant domain returns non-disclosing 404 and provider code is not invoked;
6. name.com inventory is filtered to the active tenant;
7. legacy domain attachment is explicit, idempotent, conflict-checked and reversible;
8. no historical DNS/recovery evidence table is rewritten by migration `0007`;
9. backend regression, migration drift, P3 contract, TypeScript and production build pass in CI and locally.

## Deferred to P3-C

P3-B intentionally does not tenant-scope object-by-ID lookups or rewrite derived-resource schema. P3-C will tenant-scope snapshots, known-good state, observations, incidents, explanations, recovery/emergency plans and audit events, including manipulated object IDs.
