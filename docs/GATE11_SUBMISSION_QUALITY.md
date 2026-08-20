# Gate 11 — Submission Quality

Gate 11 does not add risky product scope. It makes the existing working product reproducible, judge-readable and rehearsal-ready.

## Repository acceptance

- [x] README reflects the current product rather than the early foundation.
- [x] Architecture and trust boundaries are documented.
- [x] Environment variables and safe defaults are documented.
- [x] Clean-clone setup commands are present.
- [x] Backend and frontend verification commands are present.
- [x] Demo routes and safety procedure are present.
- [x] No secrets are required in committed files.
- [ ] Clean-clone setup is executed once on a fresh directory or machine.

## Devpost acceptance

- [x] Product name and one-line pitch prepared.
- [x] Problem and solution copy prepared.
- [x] name.com integration mapped endpoint-by-endpoint.
- [x] Build-progress story prepared.
- [x] Startup feasibility explained without claiming validated traction/pricing.
- [ ] Real screenshots captured and selected.
- [ ] Final Devpost fields copied into the submission form and reviewed.

## Demo video acceptance

Target: approximately 3 minutes unless the official challenge page requires a different duration.

- [x] Script/storyboard prepared.
- [x] Live-product-first structure prepared.
- [x] name.com actions called out visibly.
- [x] Narration emphasizes value rather than implementation trivia.
- [ ] Core recovery succeeds three consecutive rehearsals.
- [ ] Emergency flow succeeds three consecutive rehearsals.
- [ ] Final recording completed.
- [ ] Final recording watched once with sound off for visual comprehension.
- [ ] Final recording watched once audio-only for narration comprehension.

## Screenshot acceptance

Required real captures are defined in `GATE11_SCREENSHOTS.md`.

Do not substitute mockups for the real name.com-backed product where a real state exists.

## Security acceptance

Before every rehearsal and before final recording, prove safe defaults:

```text
ENV=sandbox
MUT=0
PROD_MUT=0
REG=0
AI=disabled
```

Mutation/registration may be armed only for the exact controlled step and must be reset immediately afterward.

Never perform production mutation for Gate 11.

## Final Gate 11 closure criteria

Gate 11 is complete only when all are true:

1. `python manage.py test core` passes.
2. Gate 7/8/9/10/11 contracts pass.
3. TypeScript and production build pass.
4. Clean working tree and local HEAD == remote branch HEAD.
5. `/demo` and `/feasibility` render correctly.
6. Required screenshots are real and readable.
7. Core recovery has three consecutive successful rehearsals.
8. Emergency-domain flow has three consecutive successful rehearsals.
9. Devpost copy is final.
10. Demo video is final and understandable without the README.

## Freeze boundary

Once Gate 11 passes, move to Gate 12 — Freeze. From that point, no new features; only blocker fixes, locked demo data, locked labels and locked submission copy.
