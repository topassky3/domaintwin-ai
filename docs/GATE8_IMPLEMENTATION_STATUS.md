# Gate 8 implementation status

Branch: `agent/emergency-domain-wow`
Base: Gate 7 merge on `main` (`5b4c3debc231166194d5b92c252cc596f1915690`).

Implementation is complete enough for local verification. This file intentionally does **not** claim runtime PASS: the local migration, Django tests, frontend contracts, TypeScript build, provider safe-smoke and sandbox Golden Drill are the verification gates.

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

## Verification still required locally

1. migration check + migrate;
2. Django check + full `core` test suite;
3. Gate 7 regression contract;
4. Gate 8 contract;
5. TypeScript typecheck + Next production build;
6. safe provider smoke with registration OFF;
7. controlled name.com sandbox Golden Drill;
8. restore safe runtime flags;
9. final regression + clean working tree;
10. update PR proof, ready, merge.
