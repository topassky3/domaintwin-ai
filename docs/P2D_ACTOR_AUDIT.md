# P2-D — Actor Audit Evidence

P2-D binds sensitive DomainTwin approvals and executions to the authenticated human actor without changing the deterministic recovery/emergency plan fingerprints.

## Evidence model

Actor evidence is stored inside the existing ordered audit logs instead of introducing duplicate actor columns.

Each actor snapshot contains only:

```text
userId
username
role
```

The role is resolved server-side from DomainTwin RBAC at action time. The snapshot is then persisted in the audit event so later changes to the user's current role do not rewrite historical authority.

## Recovery audit sequence

```text
PLAN_CREATED
...
PLAN_APPROVED
APPROVAL_ACTOR_RECORDED
EXECUTION_ACTOR_AUTHORIZED
APPLY_STARTED
OPERATION_*
VERIFICATION_*
RECOVERY_COMPLETED
```

`APPROVAL_ACTOR_RECORDED` binds the approver to:

- plan fingerprint
- live fingerprint at preview time
- target known-good fingerprint
- approval timestamp

`EXECUTION_ACTOR_AUTHORIZED` is appended before the recovery engine crosses the provider APPLY boundary and binds the executor to the same deterministic plan/source/target evidence.

## Emergency continuity audit sequence

```text
PLAN_CREATED
PLAN_APPROVED
APPROVAL_ACTOR_RECORDED
EXECUTION_ACTOR_AUTHORIZED
REGISTRATION_STARTED
DOMAIN_REGISTERED
CLONE_STARTED
DNS_RECORD_CLONED...
CLONE_VERIFIED
EMERGENCY_DOMAIN_READY
```

The emergency actor evidence also binds source domain, target domain and expected known-good fingerprint. Resumed emergency executions append a new executor event so retry authority remains visible in sequence order.

## API projection

Recovery and emergency plan responses derive these convenience fields from the audit log:

```text
approvedActor
executionActor
```

The audit log remains the source of truth.

## Fingerprint invariant

Actor identity is intentionally excluded from recovery and emergency fingerprint calculations.

Adding approval/execution evidence must never change:

- recovery `planFingerprint`
- recovery `liveFingerprintBefore`
- recovery `targetFingerprint`
- emergency `planFingerprint`
- emergency `expectedFingerprint`
- final verification fingerprints

This preserves the core DomainTwin invariant: deterministic state evidence is independent from the identity of the authorized human who approves or executes it.

## P2-D acceptance criteria

P2-D passes only when all of the following are true:

1. actor snapshots are derived from the authenticated Django user, never from browser-supplied actor fields;
2. actor snapshots persist stable user id, username and the server-derived DomainTwin role;
3. recovery approval appends immutable approval actor evidence;
4. idempotent reapproval cannot overwrite the original recovery approver;
5. recovery execution actor evidence is appended before provider mutation begins;
6. emergency approval appends immutable approval actor evidence;
7. emergency execution actor evidence is appended before registration/DNS mutation begins;
8. resumed emergency execution can append another ordered executor event without rewriting prior evidence;
9. recovery/emergency API responses expose audit-derived `approvedActor` and `executionActor` convenience fields;
10. actor evidence contains the relevant deterministic plan/source/target fingerprints;
11. adding actor evidence does not alter any plan fingerprint;
12. dedicated actor regressions run with production-style authentication/RBAC enforcement;
13. historical deterministic endpoint tests remain compatible only under the existing explicit Django test marker;
14. P2-D contract runs as part of `npm run p2:contract` on Windows and CI/Linux;
15. all existing Gate 7–11, P1, P2-A/B/C, Django, TypeScript and production-build regressions remain green.

## Out of scope

P2-D does not remove historical `csrf_exempt` decorators from private mutations. P2-E will close that remaining authenticated-mutation CSRF boundary and run the final end-to-end security matrix before the P2 pull request is merged.
