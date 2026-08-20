import fs from "node:fs";
import path from "node:path";

const repoRoot = path.resolve(process.cwd(), "..");
const read = (relative) => fs.readFileSync(path.join(repoRoot, relative), "utf8");
const exists = (relative) => fs.existsSync(path.join(repoRoot, relative));

const failures = [];
const requireFile = (relative) => {
  if (!exists(relative)) failures.push(`missing ${relative}`);
};
const requireText = (relative, text, label = text) => {
  if (!read(relative).includes(text)) failures.push(`${relative}: missing ${label}`);
};
const forbidText = (relative, text, label = text) => {
  if (read(relative).includes(text)) failures.push(`${relative}: stale/forbidden ${label}`);
};

const requiredFiles = [
  "README.md",
  "docs/GATE10_ARCHITECTURE_SECURITY.md",
  "docs/ENVIRONMENT_REFERENCE.md",
  "docs/GATE11_SUBMISSION_QUALITY.md",
  "docs/DEVPOST_SUBMISSION.md",
  "docs/DEMO_VIDEO_SCRIPT.md",
  "docs/GATE11_SCREENSHOTS.md",
  "docs/GATE11_REHEARSAL_RUNBOOK.md",
  "backend/.env.example",
  "frontend/.env.example",
];
requiredFiles.forEach(requireFile);

if (failures.length === 0) {
  // README is current and reproducible.
  requireText("README.md", "Detect → Explain → Restore → Prove", "core product flow");
  requireText("README.md", "SEARCH", "emergency flow");
  requireText("README.md", "Clean-clone setup", "clean clone setup");
  requireText("README.md", "python manage.py test core", "backend test command");
  requireText("README.md", "npm run gate11:contract", "Gate 11 command");
  requireText("README.md", "/demo", "public demo route");
  requireText("README.md", "/feasibility", "feasibility route");
  forbidText("README.md", "authenticated DNS operations, snapshots, incident engine, recovery engine and name.com integration are intentionally deferred", "old foundation milestone text");
  forbidText("README.md", "git checkout agent/public-landing", "obsolete branch checkout");

  // Environment/safety documentation.
  for (const variable of [
    "NAMECOM_ENVIRONMENT",
    "NAMECOM_ALLOW_MUTATIONS",
    "NAMECOM_ALLOW_PRODUCTION_MUTATIONS",
    "NAMECOM_ALLOW_DOMAIN_REGISTRATION",
    "AI_PROVIDER",
  ]) {
    requireText("docs/ENVIRONMENT_REFERENCE.md", variable);
    requireText("backend/.env.example", variable);
  }
  requireText("docs/ENVIRONMENT_REFERENCE.md", "NAMECOM_ENVIRONMENT=sandbox", "sandbox safe baseline");
  requireText("docs/ENVIRONMENT_REFERENCE.md", "NAMECOM_ALLOW_MUTATIONS=0", "mutations off baseline");
  requireText("docs/ENVIRONMENT_REFERENCE.md", "NAMECOM_ALLOW_DOMAIN_REGISTRATION=0", "registration off baseline");

  // Devpost depth: endpoint-by-endpoint sponsor integration.
  const endpoints = [
    "/core/v1/hello",
    "/core/v1/domains",
    "/core/v1/domains/{domain}/records",
    "/core/v1/domains:search",
    "/core/v1/domains:checkAvailability",
    "X-Idempotency-Key",
  ];
  endpoints.forEach((endpoint) => requireText("docs/DEVPOST_SUBMISSION.md", endpoint));
  requireText("docs/DEVPOST_SUBMISSION.md", "business-model hypothesis", "honest feasibility framing");
  requireText("docs/DEVPOST_SUBMISSION.md", "90 backend tests", "build progress evidence");

  // Video is live-product-first and contains both WOW flows.
  for (const marker of [
    "0:00–0:15",
    "CRITICAL incident",
    "Rollback preview",
    "VERIFIED RECOVERY",
    "Emergency domain search",
    "DNS clone + verify",
    "name.com",
  ]) {
    requireText("docs/DEMO_VIDEO_SCRIPT.md", marker);
  }
  requireText("docs/DEMO_VIDEO_SCRIPT.md", "show the live product", "live-product-first rule");

  // Manual evidence requirements are explicit and cannot be faked by a static contract.
  requireText("docs/GATE11_SCREENSHOTS.md", "real image files", "real screenshot manual gate");
  requireText("docs/GATE11_REHEARSAL_RUNBOOK.md", "R1 PASS", "three-run evidence template");
  requireText("docs/GATE11_REHEARSAL_RUNBOOK.md", "R2 PASS", "three-run evidence template");
  requireText("docs/GATE11_REHEARSAL_RUNBOOK.md", "R3 PASS", "three-run evidence template");
  requireText("docs/GATE11_REHEARSAL_RUNBOOK.md", "safe reset after every run", "safe reset requirement");
}

if (failures.length) {
  console.error("GATE 11 CONTRACT FAIL");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log("GATE 11 CONTRACT PASS");
console.log("Repository: current README + clean-clone/test/demo instructions present");
console.log("Environment: explicit server-side variables + sandbox fail-closed defaults documented");
console.log("Devpost: problem/solution + name.com endpoint depth + progress + honest feasibility prepared");
console.log("Video: ~3-minute live-product-first story covers recovery and emergency continuity");
console.log("Manual gates: real screenshots + 3x core rehearsal + 3x emergency rehearsal remain human-verified requirements");
