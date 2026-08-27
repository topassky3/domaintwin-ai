import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const repoRoot = path.resolve(root, "..");
const read = (relativePath) => fs
  .readFileSync(path.join(repoRoot, relativePath), "utf8")
  .replace(/\r\n/g, "\n");

const settings = read("backend/config/settings.py");
const authTests = read("backend/core/test_auth.py");
const securityTests = read("backend/core/test_security_regression.py");
const views = read("backend/core/views.py");
const twinViews = read("backend/core/twin_views.py");
const monitorViews = read("backend/core/monitor_views.py");
const aiViews = read("backend/core/ai_views.py");
const recoveryViews = read("backend/core/recovery_views.py");
const emergencyViews = read("backend/core/emergency_views.py");
const apiClient = read("frontend/src/lib/domaintwin.ts");
const packageJson = read("frontend/package.json");
const workflow = read(".github/workflows/ci.yml");
const doc = read("docs/P2E_SECURITY_REGRESSION.md");

const privateMutationViews = [
  views,
  twinViews,
  monitorViews,
  aiViews,
  recoveryViews,
  emergencyViews,
];

const checks = [
  [privateMutationViews.every((source) => !source.includes("csrf_exempt")), "private mutation views contain no csrf_exempt bypass"],
  [settings.includes("django.middleware.csrf.CsrfViewMiddleware"), "Django CSRF middleware remains enabled"],
  [apiClient.includes('import { getCsrfToken } from "@/lib/auth"') && apiClient.includes("await getCsrfToken()"), "shared private API client obtains Django CSRF token"],
  [apiClient.includes('headers.set("X-CSRFToken"') && apiClient.includes("SAFE_METHODS"), "unsafe frontend API methods attach X-CSRFToken centrally"],
  [apiClient.includes('credentials: "same-origin"'), "private browser API keeps same-origin credentials"],
  [securityTests.includes("Client(enforce_csrf_checks=True)"), "P2-E tests enforce real Django CSRF checks"],
  [securityTests.includes("test_authorized_operator_mutation_without_csrf_is_403_before_view") && securityTests.includes("client_cls.assert_not_called()"), "operator mutation without CSRF is rejected before view/provider work"],
  [securityTests.includes("test_admin_dns_mutation_without_csrf_is_403_before_provider") && securityTests.includes("client_factory.assert_not_called()"), "admin DNS mutation without CSRF is rejected before name.com work"],
  [securityTests.includes("test_valid_csrf_reaches_authorized_operator_view"), "valid CSRF crosses the CSRF boundary for an authorized role"],
  [securityTests.includes("test_valid_csrf_does_not_bypass_rbac"), "valid CSRF cannot bypass RBAC"],
  [securityTests.includes("test_anonymous_private_read_is_401"), "anonymous private API remains 401"],
  [securityTests.includes("test_logout_invalidates_private_workspace_session"), "logout invalidates subsequent private access"],
  [securityTests.includes("test_anonymous_options_remains_protocol_safe"), "OPTIONS remains protocol-safe"],
  [authTests.includes("test_login_requires_csrf") && authTests.includes("test_remember_me_uses_persistent_session_expiry") && authTests.includes("test_logout_requires_csrf_and_invalidates_session"), "existing login, remember-session and logout security regressions remain present"],
  [packageJson.includes("p2e-contract.mjs"), "cumulative P2 contract includes P2-E"],
  [workflow.includes("npm run p2:contract"), "P2-E executes through the CI P2 contract"],
  [doc.includes("P2-E acceptance criteria") && doc.includes("deterministic recovery/emergency fingerprints"), "P2-E acceptance and fingerprint invariant are documented"],
];

const failed = checks.filter(([ok]) => !ok);
if (failed.length > 0) {
  console.error("P2-E CONTRACT FAIL");
  for (const [, message] of failed) console.error(`- ${message}`);
  process.exit(1);
}

console.log("P2-E CONTRACT PASS");
for (const [, message] of checks) console.log(`- ${message}`);
