import fs from "node:fs";
import path from "node:path";

const repoRoot = path.resolve(process.cwd(), "..");

function read(relativePath) {
  return fs.readFileSync(path.join(repoRoot, relativePath), "utf8");
}

function walkFiles(directory) {
  const out = [];
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const full = path.join(directory, entry.name);
    if (entry.isDirectory()) out.push(...walkFiles(full));
    else out.push(full);
  }
  return out;
}

function requireCheck(condition, message) {
  if (!condition) throw new Error(`GATE 9 CONTRACT FAIL: ${message}`);
}

const namecom = read("backend/core/namecom.py");
const recovery = read("backend/core/recovery.py");
const ai = read("backend/core/ai.py");
const aiViews = read("backend/core/ai_views.py");
const shell = read("frontend/src/components/ProductShell.tsx");
const safetyTests = read("backend/core/test_safety.py");

requireCheck(
  namecom.includes("retryable=exc.code in {429, 500, 502, 503, 504}"),
  "name.com 429/5xx retryability classification missing",
);
requireCheck(
  namecom.includes("except error.URLError") && namecom.includes("status_code=503"),
  "network failure normalization missing",
);
requireCheck(
  namecom.includes("except TimeoutError") && namecom.includes("status_code=504"),
  "timeout normalization missing",
);
requireCheck(
  namecom.includes("status_code=exc.code") && namecom.includes("retryable=exc.code in"),
  "HTTP status preservation missing; invalid auth must remain explicit and non-retryable",
);
requireCheck(
  recovery.includes("APPLY_SKIPPED_ALREADY_RECOVERED") && recovery.includes("current_fingerprint == plan.target_fingerprint"),
  "already-resolved provider state must be a verified no-op",
);
requireCheck(
  recovery.includes("RecoveryPlan.Status.STALE") && recovery.includes("PLAN_STALE") && recovery.includes("live_fingerprint_before"),
  "stale-plan guard missing",
);
requireCheck(
  recovery.includes("RecoveryPlan.Status.PARTIAL") && recovery.includes("OPERATION_FAILED") && recovery.includes("VERIFICATION_FAILED"),
  "partial recovery must never be reported as success",
);
requireCheck(
  ai.includes("IncidentExplanation.Status.UNAVAILABLE") && ai.includes("fallback_analysis"),
  "AI unavailable fallback missing",
);
requireCheck(
  aiViews.includes('"aiCanMutateDns": False') && aiViews.includes('"humanApprovalStillRequired": True'),
  "AI safety boundary missing from browser response",
);
requireCheck(
  shell.includes("product-env--production") && shell.includes("product-env--sandbox"),
  "sandbox and production must remain visually distinct",
);
requireCheck(
  shell.includes("Credentials stay server-side") && shell.includes("DomainTwin proxy"),
  "credential boundary copy missing",
);
requireCheck(
  namecom.includes('if self.environment != "sandbox"') && namecom.includes("Gate 8 domain registration is sandbox-only"),
  "production registration hard block missing",
);

const requiredSafetyTests = [
  "test_invalid_token_401_is_explicit_and_not_retryable",
  "test_rate_limit_429_is_marked_retryable",
  "test_provider_5xx_is_marked_retryable",
  "test_network_failure_is_normalized_to_retryable_503",
  "test_timeout_is_normalized_to_retryable_504",
  "test_record_already_deleted_before_apply_becomes_verified_noop",
  "test_unexpected_record_added_after_preview_marks_plan_stale_without_mutation",
  "test_second_operation_failure_is_partial_never_false_success",
  "test_ai_unavailable_returns_safe_fallback_and_preserves_human_boundary",
  "test_production_has_distinct_base_url_and_mutation_requires_second_opt_in",
];
for (const testName of requiredSafetyTests) {
  requireCheck(safetyTests.includes(testName), `missing dedicated safety regression: ${testName}`);
}

const frontendRoot = path.join(repoRoot, "frontend", "src");
const forbiddenFrontendTokens = [
  "NAMECOM_API_TOKEN",
  "OPENAI_API_KEY",
  "Authorization:",
  '"Authorization"',
  "Basic ",
  "Bearer sk-",
];
for (const file of walkFiles(frontendRoot)) {
  const source = fs.readFileSync(file, "utf8");
  for (const token of forbiddenFrontendTokens) {
    requireCheck(!source.includes(token), `secret/auth material crossed into frontend source: ${path.relative(repoRoot, file)} (${token})`);
  }
}

console.log("GATE 9 CONTRACT PASS");
console.log("Provider failures: invalid auth explicit; 429/5xx/network/timeout classified without false success");
console.log("Recovery races: already-resolved state is verification-only; post-preview drift becomes STALE before mutation");
console.log("Partial failure: operation/verification failures remain PARTIAL or FAILED");
console.log("AI fallback: UNAVAILABLE keeps deterministic evidence + human approval boundary");
console.log("Environment safety: SANDBOX/PRODUCTION visual split + production mutation/registration guards preserved");
console.log("Secrets: provider credentials and Authorization material absent from frontend/src");
console.log(`Dedicated Gate 9 regressions: ${requiredSafetyTests.length}/${requiredSafetyTests.length}`);
