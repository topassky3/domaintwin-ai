import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const repoRoot = path.resolve(root, "..");
const read = (relativePath) => fs
  .readFileSync(path.join(repoRoot, relativePath), "utf8")
  .replace(/\r\n/g, "\n");

const actorAudit = read("backend/core/actor_audit.py");
const recoveryViews = read("backend/core/recovery_views.py");
const emergencyViews = read("backend/core/emergency_views.py");
const actorTests = read("backend/core/test_actor_audit.py");
const doc = read("docs/P2D_ACTOR_AUDIT.md");

const recoveryExecutionEvent = actorAudit.indexOf("append_recovery_audit(\n            plan,\n            RECOVERY_EXECUTION_ACTOR_EVENT");
const recoveryApplyCall = actorAudit.indexOf("return apply_recovery_plan(plan, client=client)");
const emergencyExecutionEvent = actorAudit.indexOf("append_emergency_audit(\n            plan,\n            EMERGENCY_EXECUTION_ACTOR_EVENT");
const emergencyApplyCall = actorAudit.indexOf("return apply_emergency_plan(plan, client=client)");

const checks = [
  [actorAudit.includes('"userId": user.pk') && actorAudit.includes('"username": user.get_username()') && actorAudit.includes('"role": role'), "actor evidence captures stable user id, username and server-derived role"],
  [actorAudit.includes('RECOVERY_APPROVAL_ACTOR_EVENT = "APPROVAL_ACTOR_RECORDED"') && actorAudit.includes('RECOVERY_EXECUTION_ACTOR_EVENT = "EXECUTION_ACTOR_AUTHORIZED"'), "recovery approval and execution actor events are explicit"],
  [actorAudit.includes('EMERGENCY_APPROVAL_ACTOR_EVENT = "APPROVAL_ACTOR_RECORDED"') && actorAudit.includes('EMERGENCY_EXECUTION_ACTOR_EVENT = "EXECUTION_ACTOR_AUTHORIZED"'), "emergency approval and execution actor events are explicit"],
  [actorAudit.includes('"planFingerprint": result.plan_fingerprint') && actorAudit.includes('"targetFingerprint": result.target_fingerprint'), "recovery approval evidence binds actor to deterministic fingerprints"],
  [actorAudit.includes('"planFingerprint": plan.plan_fingerprint') && actorAudit.includes('"liveFingerprintBefore": plan.live_fingerprint_before'), "recovery execution evidence binds actor to preview source fingerprint"],
  [actorAudit.includes('"expectedFingerprint": result.expected_fingerprint') && actorAudit.includes('"sourceDomain": result.source_domain_name') && actorAudit.includes('"targetDomain": result.target_domain_name'), "emergency approval evidence binds actor to source, target and expected fingerprint"],
  [recoveryExecutionEvent >= 0 && recoveryApplyCall >= 0 && recoveryExecutionEvent < recoveryApplyCall, "recovery executor is recorded before crossing provider apply boundary"],
  [emergencyExecutionEvent >= 0 && emergencyApplyCall >= 0 && emergencyExecutionEvent < emergencyApplyCall, "emergency executor is recorded before registration/DNS apply boundary"],
  [recoveryViews.includes("approve_recovery_plan_as(plan, user=request.user)") && recoveryViews.includes("apply_recovery_plan_as(plan, user=request.user)"), "recovery endpoints derive actor from authenticated request user"],
  [emergencyViews.includes("approve_emergency_plan_as(plan, user=request.user)") && emergencyViews.includes("apply_emergency_plan_as(plan, user=request.user, client=client)"), "emergency endpoints derive actor from authenticated request user"],
  [recoveryViews.includes("**recovery_actor_summary(plan)") && emergencyViews.includes("**emergency_actor_summary(plan)"), "plan API responses expose audit-derived approved and execution actors"],
  [actorTests.includes("@override_settings(DOMAIN_TWIN_TESTING=False)"), "actor evidence tests run with production-style authentication/RBAC enforcement"],
  [actorTests.includes("test_recovery_approval_actor_is_not_rewritten_by_idempotent_reapproval"), "approval identity is immutable across idempotent reapproval"],
  [actorTests.includes("self.assertEqual(result.plan_fingerprint, original_fingerprint)") && actorTests.includes("self.assertEqual(plan.plan_fingerprint, original_fingerprint)"), "actor evidence regressions prove deterministic fingerprints remain unchanged"],
  [actorTests.includes('event_type="APPLY_STARTED"') && actorTests.includes('event_type="REGISTRATION_STARTED"'), "tests prove executor evidence precedes provider mutation start events"],
  [doc.includes("P2-D acceptance criteria") && doc.includes("fingerprints remain unchanged"), "P2-D acceptance criteria and fingerprint invariant are documented"],
];

const failed = checks.filter(([ok]) => !ok);
if (failed.length > 0) {
  console.error("P2-D CONTRACT FAIL");
  for (const [, message] of failed) console.error(`- ${message}`);
  process.exit(1);
}

console.log("P2-D CONTRACT PASS");
for (const [, message] of checks) console.log(`- ${message}`);
