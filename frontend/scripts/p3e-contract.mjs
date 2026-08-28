import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const repoRoot = path.resolve(root, "..");
const read = (relativePath) => fs
  .readFileSync(path.join(repoRoot, relativePath), "utf8")
  .replace(/\r\n/g, "\n");

const tests = read("backend/core/test_tenant_security_regression.py");
const tenant = read("backend/core/tenant.py");
const twinViews = read("backend/core/twin_views.py");
const monitorViews = read("backend/core/monitor_views.py");
const monitoring = read("backend/core/monitoring.py");
const riskViews = read("backend/core/risk_views.py");
const recoveryViews = read("backend/core/recovery_views.py");
const emergencyViews = read("backend/core/emergency_views.py");
const doc = read("docs/P3E_TENANT_SECURITY_REGRESSION.md");

const checks = [
  [tests.includes("TenantAdversarialSecurityRegressionTests") && tests.includes("DOMAIN_TWIN_TESTING=False"), "P3-E runs a dedicated production-style adversarial tenant suite"],
  [tests.includes("test_cross_tenant_domain_routes_fail_before_provider_and_mutation") && tests.includes("client_factory.assert_not_called()") && tests.includes("client_cls.assert_not_called()"), "cross-tenant domain attacks prove provider pre-denial"],
  [tests.includes("test_manipulated_snapshot_ids_are_domain_bound_and_non_disclosing") && tests.includes("diff/?snapshot_id="), "snapshot and diff IDs are attacked across tenant/domain boundaries"],
  [tests.includes("test_cross_tenant_object_ids_and_actor_audit_are_hidden_before_execution") && tests.includes("TENANT_B_SECRET"), "incident/AI/recovery/emergency IDs and audit evidence are tested for non-disclosure"],
  [tests.includes("test_tampered_session_and_nonmember_selection_cannot_switch_tenant") && tests.includes("not-a-uuid"), "tampered tenant session state and non-member selection are tested"],
  [tests.includes("test_revoked_membership_and_inactive_organization_fail_before_provider") && tests.includes("test_membership_role_change_is_effective_without_relogin_or_group_override"), "revocation, deactivation and live role changes are adversarially covered"],
  [tests.includes("test_inactive_managed_domain_revokes_domain_and_derived_resource_access") && tests.includes("test_switching_active_organization_switches_data_and_role_without_bleed"), "managed-domain revocation and tenant switching are covered"],
  [tests.includes("test_corrupted_known_good_chain_fails_before_provider_across_evidence_flows") && tests.includes("test_corrupted_derived_chains_are_excluded_from_lists_and_object_ids"), "corrupted evidence chains are attacked before provider and list/object exposure"],
  [tenant.includes("require_snapshot_domain") && tenant.includes("F(root_lookup)"), "tenant core enforces exact same-domain baseline chain integrity"],
  [twinViews.includes("require_snapshot_domain") && twinViews.includes("isinstance(exc, Http404)"), "snapshot/diff views normalize corrupted or manipulated evidence to 404"],
  [monitoring.includes("require_snapshot_domain") && monitorViews.includes('baseline_snapshot__domain_name=F("domain_name")'), "monitoring validates baseline chains and filters inconsistent incidents"],
  [riskViews.includes("require_snapshot_domain"), "risk evaluation validates known-good baseline domain before provider work"],
  [recoveryViews.includes("require_snapshot_domain") && recoveryViews.includes("_consistent_recovery_rows"), "recovery preview/list/object paths enforce exact baseline and incident chain integrity"],
  [emergencyViews.includes("require_snapshot_domain") && emergencyViews.includes("_consistent_emergency_rows"), "emergency preview/list/object paths enforce exact source baseline integrity"],
  [doc.includes("P3-E acceptance criteria") && doc.includes("no schema or data migration") && doc.includes("does not change any fingerprint algorithm"), "P3-E security closure and deterministic-evidence invariants are documented"],
];

const failed = checks.filter(([ok]) => !ok);
if (failed.length > 0) {
  console.error("P3-E CONTRACT FAIL");
  for (const [, message] of failed) console.error(`- ${message}`);
  process.exit(1);
}

console.log("P3-E CONTRACT PASS");
for (const [, message] of checks) console.log(`- ${message}`);
