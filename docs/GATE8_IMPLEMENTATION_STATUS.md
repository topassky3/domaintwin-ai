# Gate 8 implementation status

Branch: `agent/emergency-domain-wow`
Base: Gate 7 merge on `main` (`5b4c3debc231166194d5b92c252cc596f1915690`).

Implementation is complete and PR #11 remains intentionally in draft until runtime proof is complete.

## Implemented

- name.com Core Search and exact Check Availability integration.
- standard non-premium `.com/.net/.org` emergency target scope.
- persistent emergency-domain plan and ordered audit trail.
- read-only preview from source known-good snapshot.
- explicit human approval.
- sandbox-only domain registration with a second default-off registration guard.
- persisted provider idempotency key and resumable `APPLYING` state for timed-out registration requests.
- post-registration target DNS read before clone.
- clone limited to CREATE-only reconciliation; unpreviewed UPDATE/DELETE is blocked.
- fresh DNS read after clone and exact fingerprint verification.
- `READY` only after expected == actual fingerprint.
- `/app/emergency` UI, permanent navigation and Overview CTA.
- Gate 8 static contract and backend regression coverage.

## Verified locally — Checkpoint 8A (2026-08-19)

- branch HEAD `63fe15667569bb5640aa17bfeb39668643ccbc13`.
- `makemigrations --check --dry-run` -> `No changes detected`.
- migration `core.0005_emergency_domain` applied successfully.
- Django system check -> no issues.
- Gate 8 focused backend tests -> 10/10 PASS.
- full `core` regression -> 80/80 PASS.
- Gate 7 contract -> PASS.
- Gate 8 contract -> PASS.
- TypeScript typecheck -> PASS.
- Next production build -> PASS, including `/app/emergency`.
- expected build artifacts were produced locally: modified `frontend/next-env.d.ts` and untracked `frontend/tsconfig.tsbuildinfo`; they must be cleaned before final merge verification.

## Verification still required locally

1. clean generated build artifacts;
2. safe provider/UI smoke with mutations OFF and registration OFF;
3. verify SEARCH -> CHECK -> PREVIEW from `/app/emergency`;
4. controlled name.com sandbox Golden Drill;
5. verify REGISTER -> CLONE -> VERIFY -> READY and exact `MATCH YES`;
6. restore safe runtime flags;
7. final regression + clean working tree;
8. update PR proof, ready, merge.
