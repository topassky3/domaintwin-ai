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

## P2-B — Private workspace boundary

P2-B closes the anonymous product surface at both layers.

Backend boundary:

```text
PUBLIC
  /api/health/
  /api/auth/*

AUTHENTICATED SESSION REQUIRED
  /api/namecom/*
  /api/twin/*
  /api/risk/*
  /api/monitor/*
  /api/incidents/*
  /api/ai/*
  /api/recovery/*
  /api/emergency/*
```

`PrivateApiSessionMiddleware` runs after Django `AuthenticationMiddleware`, so authorization decisions use the server-side session identity. Anonymous private API requests receive explicit `401` JSON and are stopped before provider or recovery view logic executes. `OPTIONS` requests remain protocol-safe.

Frontend boundary:

`frontend/src/app/app/layout.tsx` is dynamic and verifies the current Django session server-side through `/api/auth/me/` before rendering `ProductShell`. Missing, invalid or unavailable sessions redirect to `/login`.

The public product explanation and guided demonstration remain intentionally separate from the private workspace.

The historical pre-auth endpoint regression suite executes under a test-only marker so deterministic behavior tests do not need synthetic sessions added to every legacy case. Dedicated P2-B security tests explicitly disable that marker and exercise the same middleware configuration used by the running application.

## P2-B acceptance criteria

P2-B passes only when all of the following are true:

1. the private API session middleware is installed after Django authentication middleware;
2. `/api/health/` remains available anonymously;
3. `/api/auth/*` remains available for session bootstrap/login/logout/me behavior;
4. anonymous requests to a private provider/read endpoint return JSON `401` before provider code runs;
5. anonymous requests to a private recovery mutation endpoint return JSON `401` before recovery code runs;
6. an authenticated Django session can reach private query endpoints;
7. the `/app` layout performs a server-side `auth/me` session check before rendering the product shell;
8. missing or invalid workspace sessions redirect to `/login`;
9. `/demo`, `/feasibility`, `/login` and the public landing page remain outside the private `/app` layout;
10. dedicated security regressions run with production-style auth enforcement enabled;
11. P2 contract verifies both backend and frontend private boundaries;
12. existing deterministic tests, Gate 7–11, P1, TypeScript and production build remain green;
13. no DNS provider mutation, recovery planning, emergency continuity or AI decision logic changes in P2-B.

## Remaining P2 checkpoints

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
