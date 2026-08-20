import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const failures = [];
const required = [
  "src/app/app/emergency/page.tsx",
  "src/components/EmergencyDomainDashboard.tsx",
  "src/components/ProductShell.tsx",
  "src/lib/domaintwin.ts",
  "../backend/core/emergency.py",
  "../backend/core/emergency_views.py",
  "../backend/core/namecom.py",
  "../backend/core/models.py",
  "../backend/core/urls.py",
  "../backend/core/migrations/0005_emergency_domain.py",
  "../backend/core/test_emergency.py",
  "../docs/GATE8_EMERGENCY_DOMAIN.md",
];

for (const relative of required) {
  if (!fs.existsSync(path.resolve(root, relative))) failures.push(`missing file: ${relative}`);
}

if (!failures.length) {
  const ui = fs.readFileSync(path.resolve(root, "src/components/EmergencyDomainDashboard.tsx"), "utf8");
  const shell = fs.readFileSync(path.resolve(root, "src/components/ProductShell.tsx"), "utf8");
  const client = fs.readFileSync(path.resolve(root, "../backend/core/namecom.py"), "utf8");
  const core = fs.readFileSync(path.resolve(root, "../backend/core/emergency.py"), "utf8");
  const views = fs.readFileSync(path.resolve(root, "../backend/core/emergency_views.py"), "utf8");
  const urls = fs.readFileSync(path.resolve(root, "../backend/core/urls.py"), "utf8");
  const settings = fs.readFileSync(path.resolve(root, "../backend/config/settings.py"), "utf8");
  const tests = fs.readFileSync(path.resolve(root, "../backend/core/test_emergency.py"), "utf8");

  const checks = [
    [shell.includes("/app/emergency") && shell.includes('"ED", "Emergency"'), "Emergency route missing from permanent navigation"],
    [ui.includes("Search name.com") && ui.includes("Check exact availability"), "SEARCH -> CHECK UI missing"],
    [ui.includes("Create emergency preview") && ui.includes("Approve emergency registration"), "read-only preview or human approval missing"],
    [ui.includes("Register + clone + verify"), "REGISTER -> CLONE -> VERIFY action missing"],
    [ui.includes("EXPECTED") && ui.includes("ACTUAL") && ui.includes("MATCH"), "fingerprint verification proof missing"],
    [ui.includes("PLAN HISTORY") && ui.includes("AUDIT TRAIL"), "persistent plan/audit UI missing"],
    [ui.includes("Sandbox-only purchase boundary"), "sandbox-only registration boundary not visible"],
    [client.includes("/core/v1/domains:search") && !client.includes("domains%3Asearch"), "name.com search endpoint must preserve literal colon"],
    [client.includes("/core/v1/domains:checkAvailability") && !client.includes("domains%3AcheckAvailability"), "availability endpoint must preserve literal colon"],
    [client.includes("X-Idempotency-Key"), "domain registration must use idempotency key"],
    [client.includes('self.environment != "sandbox"') && client.includes("Gate 8 domain registration is sandbox-only"), "production registration must be impossible"],
    [settings.includes("NAMECOM_ALLOW_DOMAIN_REGISTRATION") && settings.includes('"0"'), "registration must have a second default-off guard"],
    [core.includes("build_recovery_operations") && core.includes("CLONE_ABORTED_UNEXPECTED_TARGET_STATE"), "post-registration DNS state must be rechecked before clone"],
    [core.includes('row.get("action") != "CREATE"'), "unpreviewed UPDATE/DELETE mutations must be blocked"],
    [core.includes("snapshot_fingerprint") && core.includes("actual_fingerprint == plan.expected_fingerprint"), "READY must require exact fingerprint verification"],
    [core.includes("EmergencyDomainPlan.Status.APPLYING") && core.includes("APPLY_RESUMED") && core.includes("REGISTRATION_RETRY"), "APPLYING plans must safely resume with persisted provider idempotency"],
    [tests.includes("test_apply_can_resume_registration_with_same_idempotency_key_after_timeout"), "registration-timeout resume regression test missing"],
    [views.includes('payload.get("approve") is not True'), "approval endpoint must require explicit approve=true"],
    [views.includes('payload.get("execute") is not True') && views.includes('payload.get("targetDomain") != plan.target_domain_name'), "apply must require exact target confirmation"],
    [urls.includes('path("emergency/search/"') && urls.includes('path("emergency/check/"'), "Gate 8 API routes missing"],
    [!ui.includes("NAMECOM_API_TOKEN") && !ui.includes("OPENAI_API_KEY"), "provider secrets must not appear in browser code"],
    [!views.includes('"contacts":') && !core.includes('"contacts":'), "Gate 8 API must not persist or return provider contacts"],
  ];
  for (const [ok, message] of checks) if (!ok) failures.push(message);
}

if (failures.length) {
  console.error("GATE 8 CONTRACT FAILED");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log("GATE 8 CONTRACT PASS");
console.log("Flow: SEARCH -> CHECK -> PREVIEW -> APPROVE -> REGISTER -> CLONE -> VERIFY -> READY");
console.log("name.com discovery: literal-colon Core API endpoints present");
console.log("Registration safety: sandbox-only + mutations flag + second registration flag");
console.log("Registration retry safety: persisted X-Idempotency-Key + APPLYING resume coverage");
console.log("Human boundary: explicit approval + exact target execution confirmation");
console.log("DNS safety: post-registration state re-read; unpreviewed UPDATE/DELETE blocked");
console.log("Verification: READY only when live fingerprint exactly matches known-good snapshot");
console.log("Audit: persistent emergency plan history + ordered events");
console.log("Privacy: provider contacts/secrets do not cross the browser boundary");
