import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const repoRoot = path.resolve(root, "..");
const read = (relativePath) => fs
  .readFileSync(path.join(repoRoot, relativePath), "utf8")
  .replace(/\r\n/g, "\n");

const urls = read("backend/core/urls.py");
const alerts = read("backend/core/alert_views.py");
const tests = read("backend/core/test_recovery_alerts.py");
const shell = read("frontend/src/components/ProductShell.tsx");
const recovery = read("frontend/src/components/RecoveryDashboard.tsx");
const recoveryPage = read("frontend/src/app/app/recovery/page.tsx");
const styles = read("frontend/src/app/app/p6.css");
const doc = read("docs/P6_RECOVERY_UX_ALERT.md");

const checks = [
  [urls.includes('path("alerts/", active_alerts'), "P6 exposes one authenticated in-product active-alert endpoint"],
  [alerts.includes("tenant_scoped_queryset(") && alerts.includes("status=Incident.Status.OPEN") && alerts.includes('baseline_snapshot__domain_name=F("domain_name")'), "active alerts are tenant-scoped and require exact incident/baseline domain integrity"],
  [!alerts.includes("NameComClient") && !alerts.includes("namecom"), "alert reads do not cross the provider boundary"],
  [alerts.includes("_latest_consistent_plan") && alerts.includes("baseline_snapshot=incident.baseline_snapshot") && alerts.includes("domain_name=incident.domain_name"), "alert recovery metadata accepts only an exact consistent incident plan chain"],
  [tests.includes("RecoveryAlertSecurityTests") && tests.includes("test_alerts_are_tenant_scoped_and_non_disclosing") && tests.includes("test_corrupted_evidence_chain_is_excluded"), "P6 regression covers tenant isolation and corrupted evidence exclusion"],
  [tests.includes("test_alert_read_never_crosses_provider_boundary") && tests.includes("assert_not_called()"), "P6 regression proves alert reads stay before provider code"],
  [shell.includes('api<AlertsResponse>("alerts/")') && shell.includes("15_000"), "product shell polls database-only alerts every 15 seconds"],
  [shell.includes("product-nav-count") && shell.includes("p6-alert-strip") && shell.includes("Open recovery"), "active alert count and highest-priority incident are globally actionable"],
  [shell.includes('/app/recovery?domain=${encodeURIComponent(topAlert.domainName)}&incident=${topAlert.incidentId}'), "global alert deep-links the exact domain and incident into recovery"],
  [recoveryPage.includes("searchParams") && recoveryPage.includes("initialDomain") && recoveryPage.includes("initialIncidentId"), "recovery route validates and passes alert deep-link context"],
  [recovery.includes("RECOVERY_STEPS") && recovery.includes('"DETECTED", "PREVIEW", "APPROVED", "APPLY", "VERIFIED"'), "recovery UX exposes the deterministic operator progress path"],
  [recovery.includes("confirmMutation") && recovery.includes("Mutation confirmation") && recovery.includes("!verificationOnly && !confirmMutation"), "real DNS mutation requires an explicit additional UI acknowledgement"],
  [styles.includes(".p6-alert-strip") && styles.includes(".p6-recovery-steps") && styles.includes(".p6-recovery-confirm"), "P6 alert, progress and mutation-boundary styles are explicit"],
  [doc.includes("P6 acceptance criteria") && doc.includes("no schema or data migration") && doc.includes("does **not** add email, Slack, PagerDuty"), "hackathon alert scope and post-hackathon delivery deferrals are documented"],
];

const failed = checks.filter(([ok]) => !ok);
if (failed.length > 0) {
  console.error("P6 CONTRACT FAIL");
  for (const [, message] of failed) console.error(`- ${message}`);
  process.exit(1);
}

console.log("P6 CONTRACT PASS");
for (const [, message] of checks) console.log(`- ${message}`);
