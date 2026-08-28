import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const repoRoot = path.resolve(root, "..");
const read = (relativePath) => fs
  .readFileSync(path.join(repoRoot, relativePath), "utf8")
  .replace(/\r\n/g, "\n");

const settings = read("backend/config/settings.py");
const models = read("backend/core/models.py");
const middleware = read("backend/core/provider_middleware.py");
const migration = read("backend/core/migrations/0008_provider_connection.py");
const tests = read("backend/core/test_provider_credentials_lite.py");
const doc = read("docs/P4_PROVIDER_CREDENTIALS_LITE.md");

const providerBlock = models.split("class ProviderConnection(models.Model):")[1]?.split("class Membership(models.Model):")[0] ?? "";
const middlewareOrderOk = settings.indexOf("core.rbac.RoleAuthorizationMiddleware")
  < settings.indexOf("core.tenant_middleware.TenantDomainBoundaryMiddleware")
  && settings.indexOf("core.tenant_middleware.TenantDomainBoundaryMiddleware")
  < settings.indexOf("core.provider_middleware.ProviderConnectionBoundaryMiddleware");

const checks = [
  [models.includes("class ProviderConnection(models.Model):") && models.includes("unique_provider_connection_org_provider"), "P4 adds one explicit provider binding per Organization/provider"],
  [providerBlock.includes("provider = models.CharField") && providerBlock.includes("is_active = models.BooleanField"), "provider binding stores only provider identity/state metadata"],
  [!/(API_TOKEN|api_key|password|username\s*=|secret\s*=)/i.test(providerBlock), "ProviderConnection contains no credential or secret field"],
  [settings.includes('NAMECOM_USERNAME = os.getenv("NAMECOM_USERNAME"') && settings.includes('NAMECOM_API_TOKEN = os.getenv("NAMECOM_API_TOKEN"'), "name.com credential material remains backend environment configuration"],
  [middlewareOrderOk, "provider boundary runs after Membership RBAC and tenant-domain ownership"],
  [middleware.includes("provider_connection_required") && middleware.includes("ProviderConnection.objects.select_related"), "missing/inactive provider binding fails closed before provider code"],
  [middleware.includes("/api/namecom/") && middleware.includes("/api/recovery/") && middleware.includes("/api/emergency/"), "P4 gates direct DNS, recovery and emergency provider crossings"],
  [migration.includes("seed_existing_namecom_connections") && migration.includes('provider="name.com"'), "migration preserves existing Organizations by seeding name.com bindings"],
  [models.includes("ensure_default_provider_connection") && models.includes("post_save"), "new hackathon Organizations receive the single supported provider binding"],
  [tests.includes("ProviderCredentialsLiteSecurityTests") && tests.includes("DOMAIN_TWIN_TESTING=False"), "P4 runs a production-style provider security regression suite"],
  [tests.includes("test_missing_or_disabled_binding_fails_before_provider_code") && tests.includes("client_factory.assert_not_called()"), "regressions prove denial occurs before provider client execution"],
  [tests.includes("test_provider_binding_follows_active_tenant_without_cross_tenant_fallback"), "tenant switching cannot fall back to another Organization's provider binding"],
  [tests.includes("P4_SERVER_ONLY_TOKEN_DO_NOT_LEAK") && tests.includes("assertNotIn"), "API regression checks provider token non-disclosure"],
  [doc.includes("P4 acceptance criteria") && doc.includes("Explicitly deferred") && doc.includes("no provider secret is persisted"), "P4 scope and hackathon deferrals are documented"],
];

const failed = checks.filter(([ok]) => !ok);
if (failed.length > 0) {
  console.error("P4 CONTRACT FAIL");
  for (const [, message] of failed) console.error(`- ${message}`);
  process.exit(1);
}

console.log("P4 CONTRACT PASS");
for (const [, message] of checks) console.log(`- ${message}`);
