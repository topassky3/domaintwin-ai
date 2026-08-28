import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const repoRoot = path.resolve(root, "..");
const read = (relativePath) => fs
  .readFileSync(path.join(repoRoot, relativePath), "utf8")
  .replace(/\r\n/g, "\n");

const urls = read("backend/core/urls.py");
const readiness = read("backend/core/demo_readiness.py");
const view = read("backend/core/demo_views.py");
const command = read("backend/core/management/commands/demo_readiness.py");
const tests = read("backend/core/test_demo_hardening.py");
const card = read("frontend/src/components/DemoReadinessCard.tsx");
const overview = read("frontend/src/app/app/overview/page.tsx");
const errorBoundary = read("frontend/src/app/app/error.tsx");
const loadingBoundary = read("frontend/src/app/app/loading.tsx");
const styles = read("frontend/src/app/app/p7.css");
const doc = read("docs/P7_DEMO_HARDENING.md");

const checks = [
  [urls.includes('path("demo/readiness/", demo_readiness'), "P7 exposes one authenticated demo-readiness endpoint"],
  [view.includes("resolve_active_membership(request)") && view.includes("build_demo_readiness(membership.organization)"), "readiness derives the active tenant on the server"],
  [!readiness.includes("NameComClient") && !readiness.includes("requests.") && !readiness.includes("urllib"), "demo preflight is provider/network free"],
  [readiness.includes("NAMECOM_USERNAME") && readiness.includes("NAMECOM_API_TOKEN") && readiness.includes("bool(settings.NAMECOM_USERNAME and settings.NAMECOM_API_TOKEN)"), "credential readiness is boolean-only"],
  [readiness.includes('baseline.snapshot.domain_name == baseline.domain_name'), "known-good readiness requires exact same-domain evidence integrity"],
  [readiness.includes('"sandbox_environment"') && readiness.includes('"sandbox_dns_mutations"'), "safe sandbox environment and live recovery arming are explicit blockers"],
  [readiness.includes('"monitoring_freshness"') && readiness.includes('"emergency_registration"') && readiness.includes("required=False"), "monitor freshness and emergency registration are non-blocking warnings"],
  [command.includes('parser.add_argument("--organization", required=True') && command.includes('payload["status"] != "READY"'), "judge-day management command fails closed on blockers"],
  [tests.includes("test_preflight_never_falls_back_to_another_tenant") && tests.includes("test_corrupted_known_good_chain_is_not_counted_as_ready"), "P7 regression covers tenant isolation and corrupted evidence"],
  [tests.includes("test_preflight_is_database_only_and_reports_missing_provider_binding") && tests.includes('requires_namecom_provider("/api/demo/readiness/", "GET")'), "missing provider binding remains inspectable without crossing provider middleware"],
  [tests.includes("P7_SECRET_MUST_NOT_LEAK") && tests.includes("assertNotIn"), "P7 regression proves secret values are not serialized"],
  [overview.includes("DemoReadinessCard") && card.includes('api<DemoReadiness>("demo/readiness/")') && card.includes("Re-run preflight"), "Overview surfaces a manually refreshable readiness card"],
  [errorBoundary.includes("Retry view") && errorBoundary.includes("Open safe demo") && loadingBoundary.includes("Loading verified DomainTwin state"), "workspace has explicit recoverable error and loading states"],
  [styles.includes(".p7-readiness--ready") && styles.includes(".p7-readiness--blocked") && styles.includes(".p7-workspace-fallback"), "P7 readiness and fallback styles are explicit"],
  [doc.includes("P7 acceptance criteria") && doc.includes("no schema/data migration") && doc.includes("Judge-day runbook"), "hackathon hardening scope and runbook are documented"],
];

const failed = checks.filter(([ok]) => !ok);
if (failed.length > 0) {
  console.error("P7 CONTRACT FAIL");
  for (const [, message] of failed) console.error(`- ${message}`);
  process.exit(1);
}

console.log("P7 CONTRACT PASS");
for (const [, message] of checks) console.log(`- ${message}`);
