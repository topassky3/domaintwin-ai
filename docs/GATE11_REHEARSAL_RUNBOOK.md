# Gate 11 — Three-Run Rehearsal Runbook

Goal: satisfy the winning-plan requirement that **core recovery** and **emergency continuity** each succeed deterministically on **three consecutive rehearsals** before final recording.

This runbook deliberately avoids unattended mutation. Every provider write remains a human-approved step.

## Safety invariants

Before each run, prove:

```text
ENV=sandbox
MUT=0
PROD_MUT=0
REG=0
AI=disabled
```

Never use production mutation.

Never paste provider credentials into screenshots, logs, chat or committed files.

After every controlled mutation/registration segment, return the flags to the safe state above before starting the next rehearsal.

## Rehearsal evidence sheet

For each run record:

```text
Run: R1 / R2 / R3
Date/time:
Source domain:
Known-good snapshot version:
Incident ID:
Recovery plan ID:
Recovery expected fingerprint:
Recovery actual fingerprint:
Recovery MATCH: YES/NO
Recovery final state:
Emergency candidate:
Emergency plan ID:
Emergency expected fingerprint:
Emergency actual fingerprint:
Emergency MATCH: YES/NO
Emergency final state:
Notes:
```

Do not include API tokens.

---

# Part A — Core recovery × 3

Use the same trusted source domain and same known-good snapshot unless a real state change makes that unsafe.

## A0. Preflight for every run

1. Backend safe flags are `sandbox / 0 / 0 / 0 / disabled`.
2. UI shows SANDBOX.
3. name.com provider status is connected.
4. Source domain is the intended controlled sandbox domain.
5. Trusted known-good snapshot is the expected version/fingerprint.
6. There is no unresolved unexpected recovery state from the previous run.

If any item differs, stop and investigate instead of adapting the demo ad hoc.

## A1. Controlled drift

Arm only DNS mutations:

```text
NAMECOM_ALLOW_MUTATIONS=1
NAMECOM_ALLOW_PRODUCTION_MUTATIONS=0
NAMECOM_ALLOW_DOMAIN_REGISTRATION=0
```

Create the same rehearsed dangerous drift used by the golden flow, using the prepared test record/value.

Perform one controlled mutation only.

## A2. Detect incident

Run/refresh the existing monitoring flow until:

- live DNS differs from known-good;
- risk factors are visible;
- incident is OPEN/CRITICAL as expected.

Record incident ID.

## A3. Explain

AI may be enabled only if the recording/rehearsal explicitly needs the live explanation and a configured provider is available.

AI failure is not allowed to block deterministic recovery.

Verify the explanation references structured incident evidence and does not propose autonomous mutation.

## A4. Preview recovery

Create/open the recovery plan.

Verify:

- exact source/target snapshot;
- exact operation list;
- no unpreviewed operation;
- plan is not stale;
- expected fingerprint matches the trusted snapshot.

## A5. Approve + apply

Approve once through the UI.

Apply once.

Do not click repeatedly while waiting.

## A6. Verify

PASS only if:

```text
RECOVERED
expected fingerprint == actual fingerprint
MATCH YES
incident RESOLVED
ordered audit present
```

Record plan ID and fingerprints.

## A7. Safe reset

Immediately restore:

```text
MUT=0
PROD_MUT=0
REG=0
AI=disabled
```

Refresh UI and confirm the recovered result remains persisted.

### Core rehearsal rule

R1, R2 and R3 must pass consecutively. If any run fails, fix the blocker and restart the consecutive count at R1.

---

# Part B — Emergency continuity × 3

Important sandbox characteristic: emergency registrations create persistent sandbox-domain artifacts. Use a **fresh unique candidate for each run** and expect those sandbox records to remain visible afterward.

Do not register three domains merely to rush the checklist. Run these rehearsals only when the submission/demo flow is otherwise stable.

## Candidate naming

Use explicit rehearsal-only names, for example:

```text
domaintwin-r1-<timestamp>.com
domaintwin-r2-<timestamp>.com
domaintwin-r3-<timestamp>.com
```

The exact candidate must still come from real Search + Check results and be available at execution time.

## B0. Preflight

1. Safe flags `sandbox / 0 / 0 / 0 / disabled`.
2. Source trusted snapshot is still the intended known-good source.
3. Registration is visibly BLOCKED initially.
4. Search/check operations work while mutations remain disabled.

## B1. SEARCH

Search a unique rehearsal keyword through the real name.com endpoint.

Record candidate list/result count if useful.

## B2. CHECK

Select a standard supported non-premium candidate and run exact availability check.

PASS only if exact candidate is `AVAILABLE` and checked.

## B3. PREVIEW

Create exactly one emergency preview.

Verify:

- exact target;
- source domain;
- trusted snapshot version;
- expected fingerprint;
- CREATE-only clone plan;
- no mutation yet.

## B4. APPROVE

Approve the exact target once while registration is still blocked.

Verify plan remains APPROVED and no registration result exists yet.

## B5. Arm registration

Only now set:

```text
ENV=sandbox
MUT=1
PROD_MUT=0
REG=1
```

Prove those flags before pressing Apply.

## B6. REGISTER + CLONE + VERIFY

Press the single `Register + clone + verify` action once.

Do not retry by creating a new plan if the UI waits. The persisted plan/idempotency path is designed to resume safely.

PASS only if:

```text
READY
expected fingerprint == actual fingerprint
MATCH YES
registration result persisted
ordered audit present
```

Record target, plan ID and fingerprints.

## B7. Safe reset

Immediately restore:

```text
ENV=sandbox
MUT=0
PROD_MUT=0
REG=0
AI=disabled
```

Refresh and confirm:

- `REGISTRATION BLOCKED`;
- completed plan still `READY`;
- `MATCH YES` remains persisted.

### Emergency rehearsal rule

R1, R2 and R3 must pass consecutively. A failed run resets the consecutive count after the blocker is fixed.

---

# Final rehearsal acceptance

Gate 11 rehearsal proof is PASS only when we have:

```text
CORE RECOVERY
R1 PASS
R2 PASS
R3 PASS

EMERGENCY CONTINUITY
R1 PASS
R2 PASS
R3 PASS
```

with safe reset after every run and no production mutation.

## Recording-domain reservation

Do **not** consume the exact emergency-domain keyword intended for the final video during rehearsal. Prepare a fresh recording candidate after the three rehearsal runs pass.
