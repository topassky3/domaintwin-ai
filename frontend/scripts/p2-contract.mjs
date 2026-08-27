import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const repoRoot = path.resolve(root, "..");

const read = (relativePath) => fs.readFileSync(path.join(repoRoot, relativePath), "utf8");

const authViews = read("backend/core/auth_views.py");
const authTests = read("backend/core/test_auth.py");
const authMiddleware = read("backend/core/auth_middleware.py");
const privateWorkspaceTests = read("backend/core/test_private_workspace.py");
const rbac = read("backend/core/rbac.py");
const rbacTests = read("backend/core/test_rbac.py");
const roleCommand = read("backend/core/management/commands/set_domaintwin_role.py");
const urls = read("backend/core/urls.py");
const settings = read("backend/config/settings.py");
const proxy = read("frontend/src/app/api/domaintwin/[...path]/route.ts");
const authClient = read("frontend/src/lib/auth.ts");
const loginPage = read("frontend/src/app/login/page.tsx");
const appLayout = read("frontend/src/app/app/layout.tsx");
const productShell = read("frontend/src/components/ProductShell.tsx");
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
  [appLayout.includes('export const dynamic = "force-dynamic"') && appLayout.includes("requireWorkspaceSession"), "private /app layout requires a runtime session check"],
  [appLayout.includes("/api/auth/me/") && appLayout.includes('redirect("/login")'), "private workspace verifies Django session and redirects anonymous users to login"],

  [rbac.includes('VIEWER = "VIEWER"') && rbac.includes('OPERATOR = "OPERATOR"') && rbac.includes('APPROVER = "APPROVER"') && rbac.includes('ADMIN = "ADMIN"'), "four explicit DomainTwin roles exist server-side"],
  [rbac.includes("ROLE_CAPABILITIES") && rbac.includes("OPERATOR_CAPABILITIES = VIEWER_CAPABILITIES") && rbac.includes("APPROVER_CAPABILITIES = OPERATOR_CAPABILITIES") && rbac.includes("ADMIN_CAPABILITIES = APPROVER_CAPABILITIES"), "RBAC capability inheritance is explicit"],
  [rbac.includes("if not matched:\n        return VIEWER") && rbac.includes("is_superuser") && rbac.includes("return ADMIN"), "default authenticated role is VIEWER and superuser resolves to ADMIN"],
  [settings.includes('"core.rbac.RoleAuthorizationMiddleware"'), "RBAC middleware is installed"],
  [settings.indexOf("core.auth_middleware.PrivateApiSessionMiddleware") < settings.indexOf("core.rbac.RoleAuthorizationMiddleware"), "RBAC runs after private session authentication"],
  [rbac.includes('BASELINE_APPROVE = "baseline:approve"') && rbac.includes('RECOVERY_PREVIEW = "recovery:preview"') && rbac.includes('RECOVERY_APPROVE = "recovery:approve"') && rbac.includes('RECOVERY_APPLY = "recovery:apply"'), "trusted baseline and recovery stages have separate capabilities"],
  [rbac.includes('EMERGENCY_PREVIEW = "emergency:preview"') && rbac.includes('EMERGENCY_APPROVE = "emergency:approve"') && rbac.includes('EMERGENCY_APPLY = "emergency:apply"'), "emergency continuity stages have separate capabilities"],
  [rbac.includes('DNS_MUTATE = "dns:mutate"') && rbac.includes('method in {"PUT", "PATCH", "DELETE"}'), "direct DNS mutation is explicitly classified"],
  [rbac.includes("UNCLASSIFIED_MUTATION") && rbac.includes("return UNCLASSIFIED_MUTATION"), "future unclassified private mutations fail closed"],
  [rbac.includes("Insufficient DomainTwin permission.") && rbac.includes('"requiredCapability"') && rbac.includes('"role"'), "RBAC denial is explicit JSON 403 with role and capability"],
  [authViews.includes("authorization_for_user(user)"), "auth/me derives role and capabilities on the server"],
  [roleCommand.includes("set_domaintwin_role") === false && roleCommand.includes("ROLE_GROUPS") && roleCommand.includes("user.groups.remove") && roleCommand.includes("user.groups.add"), "management command replaces a user's DomainTwin role deterministically"],
  [rbacTests.includes("test_authenticated_user_without_group_defaults_to_viewer") && rbacTests.includes("test_viewer_cannot_evaluate_and_provider_is_not_called") && rbacTests.includes("test_approver_can_reach_approval_but_cannot_apply") && rbacTests.includes("test_admin_can_reach_apply_view"), "dedicated RBAC tests cover role allow/deny boundaries"],
  [rbacTests.includes("test_unknown_mutation_is_fail_closed_to_admin") && rbacTests.includes("test_direct_dns_mutation_is_admin_only_and_denied_before_provider"), "RBAC regressions cover fail-closed mutations and provider pre-denial"],
  [authClient.includes("DomainTwinRole") && authClient.includes("capabilities: string[]"), "frontend session types carry server-derived RBAC identity"],
  [appLayout.includes("Promise<AuthUser>") && appLayout.includes("return session.user") && appLayout.includes("<ProductShell user={user}"), "private layout passes verified user identity into product shell"],
  [productShell.includes("user.role") && productShell.includes("user.username") && productShell.includes("await signOut()"), "private shell reflects role identity and supports real logout"],

  [workflow.includes("npm run p2:contract"), "P2 contract runs in CI"],
  [p2Doc.includes("P2-A acceptance criteria"), "P2-A acceptance criteria are documented"],
  [p2Doc.includes("P2-B acceptance criteria"), "P2-B acceptance criteria are documented"],
  [p2Doc.includes("P2-C acceptance criteria"), "P2-C acceptance criteria are documented"],
];

const failed = checks.filter(([ok]) => !ok);
if (failed.length > 0) {
  console.error("P2 CONTRACT FAIL");
  for (const [, message] of failed) console.error(`- ${message}`);
  process.exit(1);
}

console.log("P2 CONTRACT PASS");
for (const [, message] of checks) console.log(`- ${message}`);
