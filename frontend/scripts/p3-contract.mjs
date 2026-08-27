import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const repoRoot = path.resolve(root, "..");

const read = (relativePath) => fs
  .readFileSync(path.join(repoRoot, relativePath), "utf8")
  .replace(/\r\n/g, "\n");

const models = read("backend/core/models.py");
const migration = read("backend/core/migrations/0006_multitenant_foundation.py");
const migrationB = read("backend/core/migrations/0007_managed_domain.py");
const admin = read("backend/core/admin.py");
const bootstrap = read("backend/core/management/commands/bootstrap_domaintwin_org.py");
const domainBootstrap = read("backend/core/management/commands/attach_domaintwin_domains.py");
const tests = read("backend/core/test_multitenant_foundation.py");
const domainTests = read("backend/core/test_multitenant_domains.py");
const resourceTests = read("backend/core/test_multitenant_resources.py");
const rbac = read("backend/core/rbac.py");
const tenant = read("backend/core/tenant.py");
const tenantMiddleware = read("backend/core/tenant_middleware.py");
const authViews = read("backend/core/auth_views.py");
const views = read("backend/core/views.py");
const monitorViews = read("backend/core/monitor_views.py");
const recoveryViews = read("backend/core/recovery_views.py");
const emergencyViews = read("backend/core/emergency_views.py");
const aiViews = read("backend/core/ai_views.py");
const urls = read("backend/core/urls.py");
const settings = read("backend/config/settings.py");
const workflow = read(".github/workflows/ci.yml");
const doc = read("docs/P3_MULTI_TENANT.md");
const p3bDoc = read("docs/P3B_TENANT_DOMAINS.md");
const p3cDoc = read("docs/P3C_TENANT_RESOURCES.md");

const checks = [
  [models.includes("class Organization(models.Model):") && models.includes("models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)"), "Organization uses UUID primary-key identity"],
  [models.includes("class Membership(models.Model):") && models.includes("settings.AUTH_USER_MODEL") && models.includes('related_name="memberships"'), "Membership explicitly relates user and Organization"],
  [models.includes('VIEWER = "VIEWER"') && models.includes('OPERATOR = "OPERATOR"') && models.includes('APPROVER = "APPROVER"') && models.includes('ADMIN = "ADMIN"'), "Membership roles remain compatible with P2"],
  [models.includes('name="unique_membership_user_org"') && models.includes('name="membership_role_valid"'), "membership uniqueness and role validity are database constrained"],
  [models.includes("is_active = models.BooleanField(default=True)"), "tenant and membership activation state is explicit"],
  [migration.includes('name="Organization"') && migration.includes('name="Membership"') && !migration.includes('model_name="domainsnapshot"'), "P3-A migration adds tenant foundation without rewriting DNS evidence tables"],
  [admin.includes("OrganizationAdmin") && admin.includes("MembershipAdmin"), "tenant foundation is inspectable through Django admin"],
  [bootstrap.includes("transaction.atomic()") && bootstrap.includes("role_for_user(user)") && bootstrap.includes("Membership.objects.update_or_create"), "bootstrap is atomic, idempotent and copies current P2 role"],
  [bootstrap.includes('action="append"') && bootstrap.includes("required=True"), "bootstrap membership grant requires explicit usernames"],
  [tests.includes("test_same_user_can_hold_different_roles_per_organization") && tests.includes("test_duplicate_membership_is_rejected_by_database"), "foundation tests cover per-tenant roles and duplicate membership denial"],
  [tests.includes("test_bootstrap_command_copies_current_p2_role_and_is_idempotent") && tests.includes("test_bootstrap_validates_all_users_before_creating_organization"), "bootstrap idempotency and fail-before-create behavior are tested"],
  [rbac.includes("def role_for_user(user)") && !rbac.includes("Membership"), "P3 preserves P2 runtime RBAC until the P3-D membership cutover"],
  [models.includes("class ManagedDomain(models.Model):") && models.includes('related_name="managed_domains"') && models.includes("name = models.CharField(max_length=253, unique=True)"), "P3-B adds a single Organization-owned managed-domain root"],
  [models.includes("def canonical_domain_name") && models.includes("self.name = canonical_domain_name(self.name)"), "managed domain names are canonicalized before persistence"],
  [migrationB.includes('name="ManagedDomain"') && !migrationB.includes('model_name="domainsnapshot"') && !migrationB.includes('model_name="incident"'), "P3-B schema migration adds ownership root without rewriting historical evidence"],
  [tenant.includes('ACTIVE_ORGANIZATION_SESSION_KEY = "domaintwin_active_organization_id"') && tenant.includes("organization__is_active=True") && tenant.includes("is_active=True"), "active tenant is resolved from active server-side Membership state"],
  [tenant.includes("len(candidates) == 1") && tenant.includes('code="tenant_selection_required"') && tenant.includes("request.session.pop(ACTIVE_ORGANIZATION_SESSION_KEY"), "tenant resolution auto-selects one membership and fails closed on ambiguity or stale selection"],
  [tenant.includes("managed_domain_for_request") && tenant.includes("organization=membership.organization") && tenant.includes("raise Http404"), "domain ownership lookup is scoped to the resolved active Organization and non-disclosing"],
  [tenantMiddleware.includes('DOMAIN_KWARGS = ("domain_name", "source_domain")') && tenantMiddleware.includes("managed_domain_for_request") && tenantMiddleware.includes("view_kwargs[domain_key] = managed_domain.name"), "domain-name routes are tenant-gated and canonicalized before view/provider execution"],
  [settings.indexOf("core.rbac.RoleAuthorizationMiddleware") < settings.indexOf("core.tenant_middleware.TenantDomainBoundaryMiddleware"), "tenant domain boundary runs after P2 capability denial and before views"],
  [authViews.includes("auth_organizations") && authViews.includes("auth_active_organization") && urls.includes("auth/active-organization/"), "session tenant discovery and explicit selection endpoints are routed"],
  [views.includes("managed_names = set(") && views.includes("_domain_name_from_payload(row) in managed_names"), "name.com domain inventory is filtered to the active tenant"],
  [domainBootstrap.includes("LEGACY_DOMAIN_SOURCES") && domainBootstrap.includes("--from-legacy") && domainBootstrap.includes("--detach") && domainBootstrap.includes("Domain ownership conflict"), "legacy domain attachment is explicit, conflict-checked, idempotent and reversible"],
  [domainTests.includes("test_multiple_memberships_fail_closed_until_selected") && domainTests.includes("test_selection_validates_membership_and_cross_tenant_domain_is_404_before_provider"), "P3-B tests cover tenant ambiguity and cross-tenant provider pre-denial"],
  [domainTests.includes("test_provider_inventory_is_filtered_to_active_tenant") && domainTests.includes("test_domain_boundary_runs_before_snapshot_provider_call"), "P3-B tests cover inventory filtering and generic domain-route pre-denial"],
  [admin.includes("ManagedDomainAdmin"), "managed-domain ownership is inspectable in Django admin"],
  [p3bDoc.includes("P3-B acceptance criteria") && p3bDoc.includes("P3-C"), "P3-B security boundary and handoff to P3-C are documented"],
  [tenant.includes("def tenant_scoped_queryset") && tenant.includes('domain_lookups: str | tuple[str, ...]') && tenant.includes('f"{lookup}__in"'), "P3-C derives object ownership from the active ManagedDomain registry"],
  [monitorViews.includes("tenant_scoped_queryset") && monitorViews.includes('domain_lookups=("domain_name", "baseline_snapshot__domain_name")'), "incident ID lookup requires both incident and baseline domains to belong to the active tenant"],
  [recoveryViews.includes("def _tenant_plan_rows") && recoveryViews.includes('domain_lookups=("domain_name", "baseline_snapshot__domain_name")') && recoveryViews.includes("get_object_or_404(_tenant_plan_rows(request), id=plan_id)"), "recovery detail/approval/apply resolve plans inside the active tenant before mutation"],
  [emergencyViews.includes("def _tenant_plan_rows") && emergencyViews.includes('domain_lookups=("source_domain_name", "baseline_snapshot__domain_name")') && emergencyViews.includes("get_object_or_404(_tenant_plan_rows(request), id=plan_id)"), "emergency detail/approval/apply resolve plans inside the active tenant before provider execution"],
  [aiViews.includes("tenant_scoped_queryset") && aiViews.indexOf("get_object_or_404(rows, id=incident_id)") < aiViews.lastIndexOf("generate_incident_explanation(incident"), "AI incident lookup is tenant-scoped before evidence generation/provider execution"],
  [resourceTests.includes("test_cross_tenant_incident_and_ai_ids_fail_before_ai_execution") && resourceTests.includes("test_cross_tenant_recovery_ids_fail_before_approval_or_apply") && resourceTests.includes("test_cross_tenant_emergency_ids_fail_before_provider_or_mutation"), "P3-C regression tests cover cross-tenant read, AI, recovery and emergency boundaries"],
  [resourceTests.includes("test_mismatched_resource_and_baseline_tenant_fails_closed") && resourceTests.includes("test_same_tenant_object_ids_remain_readable"), "P3-C tests prove chain mismatch fails closed while same-tenant IDs still work"],
  [p3cDoc.includes("P3-C acceptance criteria") && p3cDoc.includes("no fingerprint algorithm or fingerprint input changes") && p3cDoc.includes("no schema/data migration"), "P3-C preserves deterministic evidence and documents the no-rewrite ownership strategy"],
  [workflow.includes("npm run p3:contract"), "P3 contract runs in GitHub CI"],
  [doc.includes("## P3-A acceptance criteria") && doc.includes("P3-B — Tenant-scoped domain inventory") && doc.includes("P3-E — Tenant security regression"), "P3 architecture and checkpoint acceptance criteria are documented"],
];

const failed = checks.filter(([ok]) => !ok);
if (failed.length > 0) {
  console.error("P3 CONTRACT FAIL");
  for (const [, message] of failed) console.error(`- ${message}`);
  process.exit(1);
}

console.log("P3 CONTRACT PASS");
for (const [, message] of checks) console.log(`- ${message}`);
