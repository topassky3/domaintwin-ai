# P3-D — Membership RBAC cutover

P3-D changes DomainTwin's runtime authorization authority from global Django groups to the active tenant Membership.

## Security rule

Authentication answers **who is the user**. The server-resolved active Membership answers **which Organization is active and what that user may do there**.

Django groups are retained only as P2 compatibility/bootstrap input. They no longer authorize production private API requests.

## Runtime authorization

For every private `/api/` request after session authentication:

1. classify the endpoint capability;
2. resolve the active Membership from server-side session state;
3. reject missing, revoked or ambiguous Membership context before provider/view execution;
4. derive the role and capabilities from `Membership.role`;
5. enforce the capability;
6. pass the same Membership into tenant-domain/object scoping and actor audit.

A user may therefore be `VIEWER` in Organization A and `ADMIN` in Organization B without changing accounts.

## Superusers

Django `is_superuser` is not a tenant authorization bypass. A superuser must still have an explicit active Membership, and its effective DomainTwin role is that Membership's role.

## Authentication API

`GET /api/auth/me/` now exposes:

- membership-derived `user.role` and `user.capabilities`;
- `activeOrganization`;
- `selectionRequired` when several active Memberships exist without a valid session selection;
- `tenantErrorCode` when no active Membership is available.

When selection is required, identity remains authenticated but role is `null` and capabilities are empty until `POST /api/auth/active-organization/` validates a selection.

The product shell uses `/api/auth/organizations/` and the selection endpoint to offer a server-validated Organization switcher.

## Actor audit

Approval/execution actor evidence uses the same active Membership role as request authorization. Group-derived or superuser-derived role elevation is not written into tenant audit events.

## P3-D acceptance criteria

P3-D passes when:

1. a user's role changes when the active Organization changes;
2. a global ADMIN group cannot elevate a VIEWER Membership;
3. an ADMIN Membership authorizes the ADMIN capability set regardless of legacy group state;
4. a superuser without Membership is denied and a superuser with VIEWER Membership remains VIEWER;
5. `/api/auth/me/` exposes active Organization plus membership-derived authorization;
6. multiple memberships fail closed until selection;
7. revoked session Membership cannot remain authority;
8. actor audit derives role from Membership context;
9. no schema migration or fingerprint input change is introduced;
10. backend regression, P3 contract, TypeScript, production build and local verification pass.
