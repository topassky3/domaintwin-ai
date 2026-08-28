# P4 — Provider Credentials Lite

## Hackathon objective

P4 deliberately avoids building a general-purpose secrets vault. DomainTwin currently supports one DNS/registrar provider, name.com, so the hackathon boundary is intentionally small:

1. name.com username/token remain backend-only environment configuration.
2. each Organization has an explicit ProviderConnection binding for name.com.
3. provider-crossing requests fail closed when that binding is missing or inactive.
4. authentication, Membership RBAC and ManagedDomain ownership continue to run before provider access.
5. no provider secret is persisted in ProviderConnection or returned by DomainTwin APIs.

## Credential boundary

The actual provider secret remains in backend process configuration:

- `NAMECOM_USERNAME`
- `NAMECOM_API_TOKEN`

`ProviderConnection` stores only:

- Organization
- provider identifier (`name.com`)
- active/inactive state
- timestamps

It intentionally contains no username, API token, password, API key, secret payload or encrypted-secret field. For the hackathon this is simpler and safer than inventing a custom vault.

## Tenant/provider order

Production private requests preserve the existing security sequence and add one boundary:

`session auth -> Membership RBAC -> ManagedDomain tenant ownership -> ProviderConnection -> provider code`

For provider routes without a domain in the URL (for example emergency search), the active Membership still determines the Organization whose ProviderConnection must be active.

A missing or inactive name.com binding returns HTTP 409 with code `provider_connection_required` before the view/provider client executes.

## Routes protected by the P4 boundary

The provider boundary covers the operations that can actually call name.com:

- all `/api/namecom/*` routes
- snapshot creation and live DNS diff
- DNS-backed risk evaluation
- monitor evaluation
- recovery preview creation and recovery apply
- emergency status/search/check, preview creation and apply

Read-only evidence/list/detail routes that do not call name.com are not unnecessarily blocked.

## Migration behavior

Migration `0008_provider_connection` creates the binding table and seeds an active name.com connection for Organizations that already exist. New Organizations receive the same single-provider hackathon binding automatically. The binding may be disabled or deleted to revoke provider access without touching Membership or ManagedDomain ownership.

No historical DNS evidence table, fingerprint algorithm, snapshot, incident, recovery plan or emergency plan is rewritten.

## P4 acceptance criteria

P4 is complete when all of the following hold:

- `ProviderConnection` is unique per Organization/provider.
- ProviderConnection persists no secret material.
- name.com credentials continue to come only from backend environment settings.
- provider middleware runs after RBAC and tenant-domain middleware.
- a missing/inactive binding fails before provider client code.
- switching active Organization switches the provider authorization context with no cross-tenant fallback.
- provider API responses do not expose `NAMECOM_API_TOKEN`.
- P4 regression tests pass with production-style middleware (`DOMAIN_TWIN_TESTING=False`).
- P2 and P3 contracts remain green.
- Django migration check, system check, full core tests, TypeScript check and production build remain green.

## Explicitly deferred

The following are intentionally outside hackathon P4:

- HashiCorp Vault or cloud KMS integration
- per-tenant encrypted provider tokens
- automatic credential rotation
- multi-provider secret versioning
- enterprise secrets lifecycle workflows

Those can be added after the hackathon without changing the P4 tenant authorization boundary.
