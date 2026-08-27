# P2 — Authentication + RBAC

P2 turns the hackathon-era private workspace into an authenticated and authorized product boundary while preserving the deterministic DomainTwin recovery model.

## Design principle

Identity and authorization are separate concerns:

1. establish a trustworthy server-side identity session;
2. protect the private workspace and private API surface;
3. introduce explicit roles/permissions;
4. bind sensitive recovery/emergency actions to an authenticated actor;
5. persist actor identity in audit evidence.

The recovery engine, deterministic DNS diff, fingerprint verification and provider safety switches remain unchanged unless a later P2 checkpoint explicitly requires authorization metadata.

## P2-A — Session identity foundation

P2-A uses Django authentication, sessions and CSRF. The browser talks to Django through the same-origin Next.js proxy; provider and AI credentials never cross into browser code.

Authentication endpoints:

```text
GET  /api/auth/csrf/
POST /api/auth/login/
POST /api/auth/logout/
GET  /api/auth/me/
```

Cookie policy:

```text
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
CSRF_COOKIE_HTTPONLY=True
CSRF_COOKIE_SAMESITE=Lax
```

Production HTTPS must enable `DJANGO_SECURE_COOKIES=1`.

## P2-A acceptance criteria

1. Django session, authentication and CSRF middleware remain enabled.
2. CSRF bootstrap/login/logout/me use Django primitives and real CSRF enforcement.
3. username or uniquely matching email can identify a user.
4. invalid credentials fail with `401` and do not create a session.
5. `remember=true` uses persistent expiry; default login expires with browser session.
6. the Next.js proxy forwards Cookie, X-CSRFToken and every upstream Set-Cookie value.
7. the login page performs real authentication and contains no hackathon workspace bypass.
8. Gate 7–11, P1, backend tests, TypeScript and production build remain green.

## P2-B — Private workspace boundary

Backend public allowlist:

```text
/api/health/
/api/auth/*
```

All other DomainTwin APIs require an authenticated server-side session. Anonymous private API requests return JSON `401` before provider or recovery code executes.

The `/app/*` layout verifies `/api/auth/me/` server-side before rendering the private product shell. `/`, `/demo`, `/feasibility` and `/login` remain public surfaces.

## P2-B acceptance criteria

1. `PrivateApiSessionMiddleware` runs after Django authentication middleware.
2. health and auth bootstrap remain public.
3. anonymous provider/read and mutation calls fail before view/provider logic.
4. authenticated sessions can reach private query endpoints.
5. `/app/*` is dynamic and redirects invalid sessions to `/login`.
6. dedicated security regressions exercise the production-style boundary.
7. deterministic DomainTwin behavior remains unchanged.

## P2-C — Server-side RBAC

P2-C adds an explicit role hierarchy without introducing a custom user model or a tenancy model. Django Groups carry DomainTwin role assignment; authenticated users with no DomainTwin group default to the least-privileged `VIEWER` role. Django superusers resolve to `ADMIN`.

```text
VIEWER
  read operational state and evidence

OPERATOR
  VIEWER + active evaluation, snapshot capture, AI generation,
  recovery preview, emergency discovery/preview

APPROVER
  OPERATOR + declare known-good baseline and approve recovery/emergency plans

ADMIN
  APPROVER + apply recovery, execute emergency continuity,
  direct DNS mutation and access administration
```

The role groups are:

```text
DomainTwin VIEWER
DomainTwin OPERATOR
DomainTwin APPROVER
DomainTwin ADMIN
```

Role assignment is explicit:

```text
python manage.py set_domaintwin_role <username> VIEWER
python manage.py set_domaintwin_role <username> OPERATOR
python manage.py set_domaintwin_role <username> APPROVER
python manage.py set_domaintwin_role <username> ADMIN
```

`/api/auth/me/` returns both the resolved role and the server-derived capability list. The private workspace displays that identity, but the frontend is never the authority: `RoleAuthorizationMiddleware` decides every private API request on the server.

Important state-changing capabilities include:

```text
snapshot:create
baseline:approve
evaluate
ai:generate
recovery:preview
recovery:approve
recovery:apply
emergency:discover
emergency:preview
emergency:approve
emergency:apply
dns:mutate
access:manage
```

Unclassified future private mutations are fail-closed to `ADMIN` until they are explicitly added to the policy.

## P2-C acceptance criteria

P2-C passes only when all of the following are true:

1. explicit `VIEWER`, `OPERATOR`, `APPROVER`, `ADMIN` roles exist server-side;
2. role capability inheritance is deterministic and tested;
3. authenticated users with no DomainTwin group resolve to `VIEWER`;
4. superusers resolve to `ADMIN`;
5. `RoleAuthorizationMiddleware` runs after session authentication and the private-session boundary;
6. reads require `read`, active evaluation/probing requires operator capability, approvals require approver capability, and provider mutation/apply operations require admin capability;
7. known-good baseline selection requires approver authority;
8. direct name.com DNS POST/PUT/PATCH/DELETE requires `dns:mutate`;
9. recovery/emergency PREVIEW, APPROVE and APPLY stages have separate capabilities;
10. an insufficient role receives explicit JSON `403` containing the required capability and current role;
11. denied requests are stopped before provider/recovery execution;
12. unknown future private mutations fail closed to admin-only authorization;
13. `/api/auth/me/` exposes role/capabilities derived by Django, not supplied by the browser;
14. `set_domaintwin_role` can replace a user's DomainTwin role deterministically;
15. the private shell displays authenticated username/role and supports real logout;
16. dedicated RBAC tests verify viewer/operator/approver/admin allow/deny behavior;
17. P2 contract, Gate 7–11, P1, backend regression, TypeScript and production build remain green;
18. P2-C does not change deterministic DNS diff, recovery plan fingerprints, emergency verification or provider safety switches.

## Remaining P2 checkpoints

### P2-D — Recovery actor evidence

- record who approved a recovery/emergency plan;
- record who applied it;
- include actor identity and role in ordered audit events;
- preserve deterministic plan/evidence fingerprints.

### P2-E — End-to-end security regression

- remove remaining private mutation CSRF exemptions safely;
- negative CSRF tests for authenticated mutations;
- complete role denial/allow matrix;
- session logout/expiry behavior;
- Gate 7–11/P1/P2 contracts;
- clean-tree proof;
- protected PR merge into `main`.

## Out of scope for P2

- organization/multi-tenancy ownership (P3)
- customer provider credential vault (P4)
- scheduled monitoring workers (P5)
- PostgreSQL migration (P6)
- alert delivery (P7)
- billing
- third-party SSO/OIDC
