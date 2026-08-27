import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const repoRoot = path.resolve(root, "..");

const read = (relativePath) => fs
  .readFileSync(path.join(repoRoot, relativePath), "utf8")
  .replace(/\r\n/g, "\n");

const models = read("backend/core/models.py");
const migration = read("backend/core/migrations/0006_multitenant_foundation.py");
const admin = read("backend/core/admin.py");
const bootstrap = read("backend/core/management/commands/bootstrap_domaintwin_org.py");
const tests = read("backend/core/test_multitenant_foundation.py");
const rbac = read("backend/core/rbac.py");
const workflow = read(".github/workflows/ci.yml");
const doc = read("docs/P3_MULTI_TENANT.md");

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
  [rbac.includes("def role_for_user(user)") && !rbac.includes("Membership"), "P3-A preserves P2 runtime RBAC until the later membership cutover"],
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
