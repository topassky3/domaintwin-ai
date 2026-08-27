# P2-E — End-to-end security regression

P2-E closes Authentication + RBAC by exercising the production security boundary as one system rather than as isolated features.

## Security chain

```text
Browser mutation
  -> same-origin Next proxy
  -> X-CSRFToken from Django bootstrap
  -> Django CsrfViewMiddleware
  -> authenticated session
  -> DomainTwin RBAC capability
  -> actor audit boundary
  -> deterministic operation/provider execution
```

Authentication, authorization and CSRF are independent gates. Passing one gate never bypasses another.

## CSRF policy

Private state-changing endpoints are no longer `csrf_exempt`. Django's configured `CsrfViewMiddleware` is authoritative for unsafe methods.

The shared frontend `api()` helper obtains the current Django token through `getCsrfToken()` and attaches `X-CSRFToken` to `POST`, `PUT`, `PATCH` and `DELETE` requests. Requests keep `credentials: "same-origin"` so the session and CSRF cookies remain bound to the same-origin proxy.

The login/logout flow continues to use the same bootstrap mechanism directly. The token cache is invalidated after login because Django rotates the CSRF secret when authentication succeeds.

## Expected boundary outcomes

```text
anonymous + private API                         -> 401
session + sufficient role + missing CSRF       -> 403
session + valid CSRF + insufficient role       -> 403
session + valid CSRF + sufficient role         -> view/provider boundary
logout + subsequent private API                -> 401
OPTIONS                                         -> protocol-safe, no mutation
```

## P2-E acceptance criteria

P2-E passes only when all of the following are true:

1. no private mutation view relies on `csrf_exempt`;
2. Django session, authentication and CSRF middleware remain enabled;
3. the generic frontend API client attaches a fresh/cached Django CSRF token to unsafe methods;
4. browser API calls explicitly use same-origin credentials;
5. an authenticated operator mutation without CSRF receives `403` before view/provider work;
6. an authenticated admin DNS mutation without CSRF receives `403` before name.com provider work;
7. valid CSRF allows an authorized request to cross the CSRF boundary;
8. valid CSRF does not bypass RBAC;
9. anonymous private reads remain `401`;
10. logout invalidates subsequent private access;
11. anonymous `OPTIONS` remains protocol-safe and cannot mutate state;
12. existing login CSRF, remember-session and logout regressions remain green;
13. P2-A/B/C/D contracts remain green together with P2-E;
14. Gate 7–11 and P1 remain green;
15. all backend core tests, TypeScript and production build pass;
16. `makemigrations --check --dry-run` reports no uncommitted model changes;
17. deterministic recovery/emergency fingerprints and actor-audit invariants remain unchanged;
18. the branch is clean and local HEAD matches the tested remote HEAD before the PR leaves Draft.

## P2 completion boundary

Once P2-E is verified locally and in GitHub Actions, PR #16 may leave Draft. The protected `main` ruleset must still require both repository status checks before merge.

P3 begins only after P2 is merged and local `main` is synchronized. P3 introduces organization/workspace ownership; it must not weaken the P2 authentication, CSRF, RBAC or actor-audit boundaries.
