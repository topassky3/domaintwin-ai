import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const repoRoot = path.resolve(root, "..");

const read = (relativePath) => fs.readFileSync(path.join(repoRoot, relativePath), "utf8");

const authViews = read("backend/core/auth_views.py");
const authTests = read("backend/core/test_auth.py");
const authMiddleware = read("backend/core/auth_middleware.py");
const privateWorkspaceTests = read("backend/core/test_private_workspace.py");
const urls = read("backend/core/urls.py");
const settings = read("backend/config/settings.py");
const proxy = read("frontend/src/app/api/domaintwin/[...path]/route.ts");
const authClient = read("frontend/src/lib/auth.ts");
const loginPage = read("frontend/src/app/login/page.tsx");
const appLayout = read("frontend/src/app/app/layout.tsx");
const workflow = read(".github/workflows/ci.yml");
const p2Doc = read("docs/P2_AUTH_RBAC.md");

const checks = [
  [urls.includes('path("auth/csrf/"') && urls.includes('path("auth/login/"') && urls.includes('path("auth/logout/"') && urls.includes('path("auth/me/"'), "session auth endpoints are routed"],
  [authViews.includes("authenticate(") && authViews.includes("login(request, user)") && authViews.includes("logout(request)"), "Django authentication/session primitives are used"],
  [authViews.includes("get_token(request)"), "CSRF bootstrap uses Django token generation"],
  [!authViews.includes("csrf_exempt"), "authentication endpoints are not CSRF-exempt"],
  [authViews.includes("request.user.is_authenticated"), "authenticated session identity is checked server-side"],
  [settings.includes("django.contrib.sessions.middleware.SessionMiddleware") && settings.includes("django.middleware.csrf.CsrfViewMiddleware") && settings.includes("django.contrib.auth.middleware.AuthenticationMiddleware"), "session, CSRF and authentication middleware remain enabled"],
  [settings.includes("SESSION_COOKIE_HTTPONLY = True") && settings.includes('SESSION_COOKIE_SAMESITE = "Lax"'), "session cookie is HttpOnly and SameSite=Lax"],
  [settings.includes("CSRF_COOKIE_HTTPONLY = True") && settings.includes('CSRF_COOKIE_SAMESITE = "Lax"'), "CSRF cookie policy is explicit"],
  [proxy.includes('headers.set("cookie", cookie)') && proxy.includes('headers.set("x-csrftoken", csrfToken)'), "Next proxy forwards session cookie and CSRF token"],
  [proxy.includes("getSetCookie") && proxy.includes('responseHeaders.append("set-cookie", value)'), "Next proxy returns upstream Set-Cookie headers"],
  [authClient.includes("getCsrfToken") && authClient.includes("signIn") && authClient.includes("currentSession") && authClient.includes("signOut"), "frontend auth client exposes CSRF/session operations"],
  [authClient.includes('credentials: "same-origin"'), "frontend auth requests explicitly use same-origin credentials"],
  [authClient.includes("Django rotates the CSRF secret"), "frontend invalidates cached CSRF token after login rotation"],
  [loginPage.includes('"use client"') && loginPage.includes("onSubmit={handleSubmit}") && loginPage.includes("await signIn("), "login form performs real authentication"],
  [!loginPage.includes("Authentication is intentionally deferred") && !loginPage.includes("Open live sandbox workspace"), "hackathon authentication bypass copy is removed from login"],
  [authTests.includes("Client(enforce_csrf_checks=True)"), "backend auth tests enforce real CSRF checks"],
  [authTests.includes("test_login_requires_csrf") && authTests.includes("test_logout_requires_csrf_and_invalidates_session"), "login/logout CSRF regressions are covered"],
  [settings.includes('"core.auth_middleware.PrivateApiSessionMiddleware"'), "private API session middleware is installed"],
  [settings.indexOf("django.contrib.auth.middleware.AuthenticationMiddleware") < settings.indexOf("core.auth_middleware.PrivateApiSessionMiddleware"), "private API boundary runs after Django authentication middleware"],
  [authMiddleware.includes('PUBLIC_API_PATHS = {"/api/health/"}') && authMiddleware.includes('PUBLIC_API_PREFIXES = ("/api/auth/",)'), "health and auth bootstrap are the explicit public backend allowlist"],
  [authMiddleware.includes("request.user.is_authenticated") && authMiddleware.includes("Authentication required."), "anonymous private API requests fail closed with JSON 401"],
  [privateWorkspaceTests.includes("@override_settings(DOMAIN_TWIN_TESTING=False)"), "private-boundary security tests use production-style auth enforcement"],
  [privateWorkspaceTests.includes("test_anonymous_private_provider_endpoint_is_blocked_before_view") && privateWorkspaceTests.includes("client_factory.assert_not_called()"), "anonymous provider access is blocked before provider code executes"],
  [privateWorkspaceTests.includes("test_anonymous_private_mutation_endpoint_is_blocked") && privateWorkspaceTests.includes("test_authenticated_session_reaches_private_query_endpoint"), "anonymous mutation denial and authenticated private access are covered"],
  [appLayout.includes('export const dynamic = "force-dynamic"') && appLayout.includes("await requireWorkspaceSession()"), "private /app layout requires a runtime session check"],
  [appLayout.includes("/api/auth/me/") && appLayout.includes('redirect("/login")'), "private workspace verifies Django session and redirects anonymous users to login"],
  [workflow.includes("npm run p2:contract"), "P2 contract runs in CI"],
  [p2Doc.includes("P2-A acceptance criteria"), "P2-A acceptance criteria are documented"],
  [p2Doc.includes("P2-B acceptance criteria"), "P2-B acceptance criteria are documented"],
];

const failed = checks.filter(([ok]) => !ok);
if (failed.length > 0) {
  console.error("P2 CONTRACT FAIL");
  for (const [, message] of failed) console.error(`- ${message}`);
  process.exit(1);
}

console.log("P2 CONTRACT PASS");
for (const [, message] of checks) console.log(`- ${message}`);
