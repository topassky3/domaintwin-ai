# P2 — Authentication + RBAC

P2 turns the hackathon-era private workspace into an authenticated product boundary while preserving the deterministic DomainTwin recovery model.

## Design principle

Identity and authorization are separate concerns:

1. establish a trustworthy server-side identity session;
2. protect the private workspace and private API surface;
3. introduce explicit roles/permissions;
4. bind sensitive recovery/emergency actions to an authenticated actor;
5. persist actor identity in audit evidence.

The recovery engine, deterministic DNS diff, fingerprint verification and provider safety switches remain unchanged unless a later P2 checkpoint explicitly requires authorization metadata.

## P2-A — Session identity foundation

P2-A uses Django's built-in authentication, session and CSRF middleware. No JWT package or external identity dependency is introduced.

Browser flow:

```text
Browser
  -> same-origin Next.js /api/domaintwin proxy
  -> Django auth/csrf
  -> Django auth/login
  -> HttpOnly session cookie
  -> auth/me proves current server-side identity
```

The Next.js proxy forwards browser cookies and the `X-CSRFToken` header to Django, and forwards Django `Set-Cookie` headers back to the browser.

Authentication endpoints:

```text
GET  /api/auth/csrf/
POST /api/auth/login/
POST /api/auth/logout/
GET  /api/auth/me/
```

The login endpoint accepts a username or a uniquely matching email address. Invalid or ambiguous identities fail closed.

`Keep me signed in` controls Django session expiry. Without it, the session expires when the browser session ends. With it, the configured persistent session lifetime is used.

## Cookie policy

P2-A makes the cookie policy explicit:

```text
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
CSRF_COOKIE_HTTPONLY=True
CSRF_COOKIE_SAMESITE=Lax
```

Local HTTP development keeps secure-cookie flags off. Production HTTPS must set:

```text
DJANGO_SECURE_COOKIES=1
```

The CSRF cookie is HttpOnly; JavaScript receives the current CSRF token through the explicit bootstrap endpoint instead of reading document cookies.

## P2-A acceptance criteria

P2-A passes only when all of the following are true:

1. Django session, authentication and CSRF middleware remain enabled.
2. `/api/auth/csrf/` returns a real Django CSRF token and creates the CSRF cookie.
3. `/api/auth/login/` is CSRF-protected and accepts valid username/password credentials.
4. a uniquely matching email address may also identify a user.
5. invalid credentials return `401` without creating a session.
6. `/api/auth/me/` returns `401` anonymously and the authenticated user after login.
7. `/api/auth/logout/` is CSRF-protected and invalidates the session.
8. default sessions expire at browser close; `remember=true` uses persistent expiry.
9. the Next.js proxy forwards Cookie and X-CSRFToken upstream.
10. the Next.js proxy forwards all upstream Set-Cookie values back to the browser.
11. the login page performs real authentication and removes the hackathon workspace-bypass link.
12. provider and AI credentials remain server-side.
13. existing Gate 7/8/9/10/11 and P1 contracts remain green.
14. the new P2 contract passes locally and in GitHub Actions.
15. all backend core tests pass with the new authentication regressions included.
16. no recovery, emergency, risk or AI decision behavior is changed in P2-A.

## Remaining P2 checkpoints

### P2-B — Private workspace boundary

- require an authenticated session for `/app/*` private product routes;
- protect private backend read/evaluation endpoints;
- preserve `/`, `/demo`, `/feasibility`, `/login` and auth bootstrap as intentional public surfaces;
- make unauthenticated API calls fail with explicit `401` JSON instead of redirects/HTML.

### P2-C — RBAC model

Introduce explicit product roles, initially:

```text
VIEWER   -> read operational state/evidence
OPERATOR -> evaluate, create recovery previews, generate explanations
APPROVER -> approve recovery/emergency plans
ADMIN    -> apply provider mutations and manage access
```

Exact permissions will be encoded and tested server-side; the frontend must never be the authorization authority.

### P2-D — Recovery actor evidence

- record who approved a plan;
- record who applied a plan;
- include actor identity in ordered audit events;
- preserve deterministic plan/evidence fingerprints.

### P2-E — End-to-end security regression

- anonymous boundary tests;
- role denial/allow matrix;
- CSRF negative tests;
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
