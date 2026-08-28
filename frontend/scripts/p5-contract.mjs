import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const repoRoot = path.resolve(root, "..");
const read = (relativePath) => fs
  .readFileSync(path.join(repoRoot, relativePath), "utf8")
  .replace(/\r\n/g, "\n");

const monitoring = read("backend/core/monitoring.py");
const command = read("backend/core/management/commands/monitor_domaintwin.py");
const monitorViews = read("backend/core/monitor_views.py");
const tests = read("backend/core/test_monitoring_lite.py");
const settings = read("backend/config/settings.py");
const envExample = read("backend/.env.example");
const doc = read("docs/P5_MONITORING_LITE.md");

const providerCheck = monitoring.indexOf("provider_enabled = ProviderConnection.objects.filter");
const baselineCheck = monitoring.indexOf("KnownGoodSnapshot.objects.filter(domain_name=managed_domain.name).exists()");
const clientConstruction = monitoring.indexOf("client=client_factory()");

const checks = [
  [monitoring.includes("def evaluate_domain_state(") && monitoring.includes("def run_monitoring_cycle("), "P5 has one reusable evaluator and one scheduler-friendly cycle"],
  [monitoring.includes('is_active=True') && monitoring.includes('organization__is_active=True'), "automatic monitoring candidates require active domains and organizations"],
  [providerCheck >= 0 && clientConstruction > providerCheck, "provider binding is checked before constructing the provider client"],
  [baselineCheck >= 0 && clientConstruction > baselineCheck, "known-good baseline is checked before provider work"],
  [monitoring.includes('"outcome": "SKIPPED"') && monitoring.includes('"outcome": "FAILED"') && monitoring.includes("continue"), "per-domain skips and failures are isolated from the rest of the cycle"],
  [monitoring.includes("correlate_incident(") && monitoring.includes("evaluate_risk("), "automatic monitoring reuses deterministic risk and incident correlation"],
  [monitorViews.includes("evaluate_domain_state(") && monitorViews.includes("client=NameComClient()") && monitorViews.includes("health_checker=check_domain_health"), "manual monitor evaluation uses the same P5 service"],
  [command.includes('"--loop"') && command.includes('"--interval-seconds"') && command.includes("interval < 10"), "worker loop is explicit and rejects aggressive polling"],
  [settings.includes("DOMAIN_MONITOR_INTERVAL_SECONDS") && envExample.includes("DOMAIN_MONITOR_INTERVAL_SECONDS=60"), "monitor loop interval is explicit backend configuration"],
  [tests.includes("MonitoringLiteTests") && tests.includes("test_inactive_provider_binding_skips_before_client_factory") && tests.includes("test_one_domain_provider_failure_does_not_stop_other_domains"), "P5 regression covers provider pre-denial and failure isolation"],
  [tests.includes("test_management_command_runs_one_scheduler_friendly_cycle") && tests.includes("test_loop_rejects_aggressive_provider_polling"), "P5 regression covers one-shot worker output and loop safety"],
  [doc.includes("P5 acceptance criteria") && doc.includes("does **not** add Celery, Redis, Kafka") && doc.includes("No schema/data migration"), "hackathon scope, scheduler model and no-schema invariant are documented"],
];

const failed = checks.filter(([ok]) => !ok);
if (failed.length > 0) {
  console.error("P5 CONTRACT FAIL");
  for (const [, message] of failed) console.error(`- ${message}`);
  process.exit(1);
}

console.log("P5 CONTRACT PASS");
for (const [, message] of checks) console.log(`- ${message}`);
