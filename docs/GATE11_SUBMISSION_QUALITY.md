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
- [x] Clean-clone setup was executed from a fresh directory: backend install/migrations/check, 90/90 core tests, Gate 7/8/9/10/11 contracts, TypeScript and production build all passed; generated artifacts were cleaned and the clone returned to a clean tree.

## Devpost acceptance

- [x] Product name and one-line pitch prepared.
- [x] Problem and solution copy prepared.
- [x] name.com integration mapped endpoint-by-endpoint.
- [x] Build-progress story prepared.
- [x] Startup feasibility explained without claiming validated traction/pricing.
- [x] Minimum strong real screenshot set captured and visually reviewed: CRITICAL incident, recovery PREVIEW, RECOVERED/MATCH YES, emergency SEARCH/CHECK, and emergency READY/MATCH YES.
- [x] Final demo-video URL synced into `DEVPOST_SUBMISSION.md`.
- [ ] Final Devpost fields reviewed immediately before submission, including sponsor selection and downloadable MP4 backup link.

## Demo video acceptance

Target: approximately 3 minutes unless the official challenge page requires a different duration.

- [x] Script/storyboard prepared.
- [x] Live-product-first structure prepared.
- [x] name.com actions called out visibly.
- [x] Narration emphasizes value rather than implementation trivia.
- [x] Core recovery succeeded three consecutive controlled rehearsals with safe reset after each run.
- [x] Emergency flow succeeded three consecutive controlled rehearsals with a fresh sandbox target per run and safe reset after each run.
- [x] Final recording completed and uploaded as an unlisted video: `https://youtu.be/6PZ8M8ZfGcc`.
- [ ] Final recording watched once with sound off for visual comprehension.
- [ ] Final recording watched once audio-only for narration comprehension.

## Screenshot acceptance

Required real captures are defined in `GATE11_SCREENSHOTS.md`.

The minimum strong set has been captured from the real name.com-backed sandbox product and reviewed for readability. Screenshots are intended for the Devpost submission; they must not expose credentials, `.env` content, terminals containing tokens, or browser developer tools with Authorization material.

Do not substitute mockups for the real name.com-backed product where a real state exists.

## Rehearsal evidence summary

- Core recovery R1/R2/R3: PASS.
- Emergency continuity R1/R2/R3: PASS.
- Known-good DNS fingerprint used for verification: `a3b35ae6406fccc24e82a5a9f3524826c5c4c88ce61ef881292837d1dad54313`.
- Controlled recovery-preview capture used a real sandbox drift, then completed recovery and returned the runtime to safe flags.
- No production mutation was enabled during Gate 11 evidence capture.

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

## H0 — Finish Hackathon closeout

H0 is intentionally documentation-and-verification only. No new product feature or risky refactor belongs in this closeout.

Close H0 in this order:

1. synchronize the local Gate 11 branch with the final remote documentation commit;
2. verify safe runtime flags;
3. run Django migration drift check and Django system check;
4. run the full 90-test backend core regression;
5. run Gate 7/8/9/10/11 contracts;
6. run TypeScript and the production Next.js build;
7. remove generated frontend artifacts if the checks modify tracked/generated files;
8. run `git diff --check` and prove a clean working tree;
9. prove local HEAD equals remote Gate 11 HEAD;
10. review the final video once with sound off and once audio-only;
11. review every Devpost field, sponsor selection, YouTube demo URL and downloadable MP4 backup link;
12. only after all checks pass, mark PR #14 ready for review and merge it to `main`;
13. enter Gate 12 Freeze: no new features, blocker fixes only.

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

Items 6–8 and final recording are satisfied. Items 1–5 must be re-run once more against the final H0 documentation state. Item 9 requires the final Devpost form review. Item 10 requires the two final playback reviews.

## Freeze boundary

Once Gate 11 passes, move to Gate 12 — Freeze. From that point, no new features; only blocker fixes, locked demo data, locked labels and locked submission copy.
