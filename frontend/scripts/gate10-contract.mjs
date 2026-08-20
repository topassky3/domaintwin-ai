import fs from "node:fs";
import path from "node:path";

const root = path.resolve(process.cwd(), "..");

function read(relativePath) {
  const absolute = path.join(root, relativePath);
  if (!fs.existsSync(absolute)) throw new Error(`Missing required Gate 10 file: ${relativePath}`);
  return fs.readFileSync(absolute, "utf8");
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const page = read("frontend/src/app/feasibility/page.tsx");
const startup = read("docs/GATE10_STARTUP_FEASIBILITY.md");
const architecture = read("docs/GATE10_ARCHITECTURE_SECURITY.md");
const namecom = read("backend/core/namecom.py");
const recovery = read("backend/core/recovery.py");
const ai = read("backend/core/ai.py");
const views = read("backend/core/views.py");

const judgeQuestions = [
  "Who pays?",
  "What do they avoid?",
  "Why DomainTwin?",
  "Why name.com?",
  "What becomes SaaS?",
];
for (const question of judgeQuestions) {
  assert(page.includes(question), `Public feasibility page missing judge question: ${question}`);
}

assert(page.includes("BUSINESS MODEL HYPOTHESIS"), "Feasibility page must label the business model as a hypothesis.");
assert(page.includes("POST-HACKATHON ROADMAP"), "Feasibility page must expose the post-hackathon roadmap.");
assert(page.includes("Recurring protection"), "Feasibility page must explain recurring SaaS economics.");
assert(page.includes("WHY NAME.COM IS CENTRAL"), "Feasibility page must visibly explain name.com centrality.");
assert(page.includes("expected and actual normalized DNS fingerprints to match"), "Feasibility page must connect commercial value to verified recovery.");

for (const phrase of [
  "Primary customer",
  "paid problem",
  "Business model hypothesis",
  "Post-hackathon roadmap",
  "Judge-ready answer",
  "name.com is structurally required",
]) {
  assert(startup.toLowerCase().includes(phrase.toLowerCase()), `Startup feasibility doc missing: ${phrase}`);
}

assert(startup.includes("agencies, MSPs, DevOps/platform teams"), "Target customer must be explicit.");
assert(startup.includes("Recurring subscription with portfolio/domain limits"), "Revenue mechanism must be explicit.");
assert(startup.includes("not a claim of validated pricing or market traction"), "Unvalidated business assumptions must be labeled honestly.");

for (const phrase of [
  "flowchart LR",
  "Next.js Web App",
  "Django API",
  "name.com Core API",
  "Persistent Store",
  "Optional AI Explanation Provider",
  "Human approval",
  "expectedFingerprint == actualFingerprint",
  "Production hardening still required after hackathon",
]) {
  assert(architecture.includes(phrase), `Architecture/security doc missing: ${phrase}`);
}

assert(namecom.includes("NAMECOM_ALLOW_PRODUCTION_MUTATIONS"), "Production mutation opt-in guard must remain present.");
assert(namecom.includes("NAMECOM_ALLOW_DOMAIN_REGISTRATION"), "Emergency registration guard must remain present.");
assert(namecom.includes('self.environment != "sandbox"'), "Emergency registration must remain sandbox-only.");
assert(recovery.includes("RecoveryStalePlan"), "Recovery stale-plan boundary must remain present.");
assert(recovery.includes("current_fingerprint != plan.live_fingerprint_before"), "Recovery must re-read and compare live state before mutation.");
assert(recovery.includes('verification["matched"]'), "Recovery success must remain fingerprint-verification dependent.");
assert(ai.includes("AI incident explanation is disabled by configuration."), "AI must remain optional.");
assert(ai.includes("AI analysis unavailable; no probable cause was generated."), "AI unavailability must preserve a deterministic fallback.");
assert(views.includes("_safe_domain_payload"), "Registrar domain payload must remain filtered at the browser boundary.");

const frontendRoot = path.join(root, "frontend", "src");
function walk(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name);
    return entry.isDirectory() ? walk(full) : [full];
  });
}
const frontendText = walk(frontendRoot)
  .filter((file) => /\.(ts|tsx|js|jsx)$/.test(file))
  .map((file) => fs.readFileSync(file, "utf8"))
  .join("\n");
assert(!frontendText.includes("NAMECOM_API_TOKEN"), "Provider API token identifier must not appear in frontend/src.");
assert(!frontendText.includes("Authorization: Basic"), "Provider Basic Authorization material must not appear in frontend/src.");

console.log("GATE 10 CONTRACT PASS");
console.log("30-second judge test: customer, paid event, differentiation, name.com centrality, SaaS path are explicit");
console.log("Business model: recurring portfolio subscription is clearly labeled as an unvalidated hypothesis");
console.log("Architecture: browser -> proxy -> Django -> name.com, persistence, health and optional AI are documented");
console.log("Security: server-side credentials, human approval, stale-plan guard, environment guards and exact verification preserved");
console.log("Roadmap: multi-tenancy, scheduling, alerts, RBAC, billing and operational hardening are separated from proven core recovery");
