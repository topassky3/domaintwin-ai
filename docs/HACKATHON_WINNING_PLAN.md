# DomainTwin AI — Hackathon Winning Plan

## Goal

Build the strongest possible submission for the DevNetwork [API + Cloud + AI] Hackathon 2026, with DomainTwin AI targeting the name.com Domain API Challenge while remaining credible for the overall hackathon judging.

Core product story:

> Detect dangerous DNS changes, explain what broke, restore a verified known-good configuration, and prove recovery.

Second WOW flow:

> When the primary domain cannot be safely recovered, search, register and configure an emergency domain through name.com.

## Judging alignment

### Overall DevNetwork judging

We must demonstrate:

- **Progress** — substantial working product built during the event.
- **Concept** — a clear real-world problem with an understandable solution.
- **Feasibility** — a credible path from hackathon project to SaaS/business.

### name.com sponsor judging

The implementation must visibly optimize for:

- API integration depth.
- Creativity / originality.
- Technical execution.
- Real-world viability.
- Presentation / demo clarity.

## Strategic rule

Every task must strengthen at least one of these two flows:

1. **Detect → Explain → Restore → Prove**
2. **Search → Check → Register → Clone → Verify**

Anything that does not materially strengthen these flows is P1/P2.

---

# Authentication decision

## Do NOT prioritize public user registration yet

A real self-service signup flow is not required for the core hackathon value proposition and does not materially improve name.com API depth.

For judges:

- `/demo` must remain accessible without authentication.
- `/login` communicates the future SaaS boundary.
- Real registration/authentication is deferred until the DNS recovery flow is complete.

### Optional P1 authentication gate

Only implement signup/authentication after Gate 7 is complete.

Minimum acceptable P1 auth:

- Create account with email + password.
- Password securely hashed by Django auth.
- Login/logout works.
- `/app/*` requires authentication.
- A new user reaches the name.com onboarding flow after login.
- `/demo` remains public and frictionless.

Do not implement OAuth, password reset, organizations, invitations or complex RBAC during the hackathon.

---

# Current completed foundation

- [x] GitHub repository initialized.
- [x] Next.js frontend foundation.
- [x] Django backend foundation.
- [x] `GET /api/health/`.
- [x] Public landing page.
- [x] Sign-in view.
- [x] Public guided hackathon demo view.
- [x] Public/private product boundary established.

---

# Gate 1 — name.com Core Integration

## Tasks

- Configure name.com Sandbox and Production environments via env vars.
- Implement backend name.com API client.
- Authenticate successfully against sandbox.
- List domains.
- Read a domain.
- Read DNS records.
- Create DNS record.
- Update DNS record.
- Delete DNS record.
- Normalize API errors.
- Ensure credentials never reach frontend/logs.

## Acceptance criteria

Gate passes only if:

- [ ] `GET domains` returns real sandbox data through our backend.
- [ ] `GET records` returns real records through our backend.
- [ ] A controlled DNS record can be created, updated and deleted through DomainTwin backend.
- [ ] Sandbox/Production selection requires no code change.
- [ ] 401/403/404/409/422/429/5xx/timeout have explicit handling paths.
- [ ] No API token appears in browser network payloads, logs or committed code.
- [ ] A short integration test/demo can prove name.com is structurally required.

**Winning impact:** Very high — API depth + technical execution.

---

# Gate 2 — Digital Twin / Snapshot Engine

## Tasks

- DNS record normalization.
- Snapshot model.
- Known-good marker.
- Snapshot versioning.
- Deterministic diff engine.

Canonical normalized record:

```text
type
host
answer
ttl
priority
```

Diff states:

```text
ADDED
REMOVED
MODIFIED
UNCHANGED
```

## Acceptance criteria

- [ ] A live name.com DNS state can be saved as a snapshot.
- [ ] Snapshot remains immutable when live DNS changes.
- [ ] A snapshot can be explicitly marked `KNOWN_GOOD`.
- [ ] Diff correctly detects added, removed and modified records.
- [ ] Before/after values are preserved.
- [ ] Unit tests cover normalization and diff behavior.
- [ ] Diff executes fast enough to feel instant for small DNS configurations.

**Winning impact:** High — originality + product credibility.

---

# Gate 3 — Deterministic Risk Engine

## Tasks

Initial transparent rules:

```text
A/AAAA production changed  +30
MX removed                 +30
NS modified                +35
HTTP health failed         +30
Unknown destination        +15
TXT changed                 +5
```

Severity:

```text
0–24   LOW
25–49  MEDIUM
50–74  HIGH
75–100 CRITICAL
```

## Acceptance criteria

- [ ] Score is deterministic.
- [ ] Score is capped at 100.
- [ ] Every score exposes contributing factors.
- [ ] Same evidence always produces same score.
- [ ] Unit tests cover representative HIGH/CRITICAL cases.
- [ ] UI never displays a risk score without explanation.

**Winning impact:** High — technical trust and differentiation.

---

# Gate 4 — Health + Incident Detection

## Tasks

- HTTP health check.
- HTTPS health check.
- Incident model/state machine.
- Correlate DNS drift and availability failure.
- Incident timeline.

## Acceptance criteria

- [ ] Domain starts HEALTHY.
- [ ] Controlled dangerous DNS change is detected.
- [ ] Health failure is recorded independently from DNS diff.
- [ ] Relevant drift/failure creates an incident automatically.
- [ ] Incident contains timestamps, score, factors and evidence.
- [ ] Timeline ordering is deterministic and understandable.
- [ ] Re-running checks does not create duplicate incidents for the same active event.

**Winning impact:** Very high — core concept becomes real.

---

# Gate 5 — Recovery Engine

## Tasks

- Rollback planner.
- Preview CREATE / UPDATE / DELETE operations.
- Human approval.
- Apply operations through name.com.
- Idempotency.
- Partial recovery state.
- Post-recovery DNS verification.
- Audit log.

## Acceptance criteria

- [ ] DomainTwin generates a rollback plan from Current → Known-Good.
- [ ] User sees exact operations before mutation.
- [ ] No mutation occurs without explicit human confirmation.
- [ ] Repeating the same recovery does not duplicate records.
- [ ] Each name.com operation result is logged.
- [ ] Failure on operation N produces `PARTIAL RECOVERY`, never false success.
- [ ] Expected DNS and actual DNS are compared after mutation.
- [ ] `RECOVERED` is shown only when verification passes.
- [ ] Tests cover rollback planning and idempotent behavior.

## Golden Gate

If this works end-to-end:

```text
Healthy
→ dangerous DNS change
→ CRITICAL incident
→ rollback preview
→ human confirm
→ name.com mutation
→ verification
→ RECOVERED
```

we already have a serious hackathon submission.

**Winning impact:** Maximum — central demo moment.

---

# Gate 6 — AI Incident Explanation

## Tasks

Feed only structured evidence:

```text
previous_state
current_state
dns_diff
health_checks
risk_score
timestamps
```

Expected output:

```text
probable_cause
affected_service
evidence
recommended_action
confidence
```

## Acceptance criteria

- [ ] AI explanation references only evidence present in the incident.
- [ ] Prompt forbids invented DNS changes.
- [ ] Output distinguishes fact from probable cause.
- [ ] AI never directly executes CREATE/UPDATE/DELETE/REGISTER.
- [ ] If AI is unavailable, diff/risk/recovery remain fully functional.
- [ ] Demo visibly labels AI as evidence-based analysis.

**Winning impact:** Medium-high — AI value without black-box risk.

---

# Gate 7 — Private Product UI

## Required routes

```text
/app/overview
/app/domains
/app/domains/:domain
/app/domains/:domain/dns
/app/domains/:domain/snapshots
/app/incidents
/app/incidents/:id
/app/recovery
```

## Acceptance criteria

- [ ] UI matches approved Stitch visual language.
- [ ] Permanent SANDBOX/PRODUCTION indicator.
- [ ] Judge understands domain, status, risk, change and action in <15 seconds.
- [ ] `acme.com` demo can travel through every core screen without dead ends.
- [ ] Healthy → Critical → Recovered transition is visually obvious.
- [ ] name.com operations are visible enough that integration depth is undeniable.
- [ ] Loading/error/empty states exist for external calls.

**Winning impact:** High — presentation + product viability.

---

# Gate 8 — Emergency Domain WOW Flow

## Tasks

- Search domain candidates through name.com.
- Check availability.
- Recheck before registration.
- Human confirmation.
- Register controlled emergency domain in sandbox/demo environment.
- Generate DNS clone plan.
- Apply selected DNS records.
- Verify destination DNS.

## Acceptance criteria

- [ ] Search uses real name.com endpoint.
- [ ] Availability uses real name.com endpoint.
- [ ] Registration uses real name.com endpoint in allowed demo environment.
- [ ] Human approval precedes registration.
- [ ] Clone preview clearly identifies domain-specific records requiring review.
- [ ] Destination records are re-read after clone.
- [ ] Final state is `READY`, `PARTIAL` or `FAILED` — never false success.
- [ ] Demo shows `SEARCH → CHECK → REGISTER → CLONE → VERIFY` clearly.

**Winning impact:** Maximum for sponsor API-depth criterion.

---

# Gate 9 — Edge Cases + Safety

## Acceptance criteria

Must deliberately demonstrate/test:

- [ ] invalid name.com token.
- [ ] 429 rate limit.
- [ ] timeout / 5xx.
- [ ] record already deleted.
- [ ] record unexpectedly added.
- [ ] partial rollback.
- [ ] AI provider unavailable.
- [ ] stale snapshot warning.
- [ ] sandbox vs production visual separation.
- [ ] secrets absent from repo and frontend.

**Winning impact:** High — technical execution.

---

# Gate 10 — Startup / Feasibility Proof

## Deliverables

- Target customer: agency/MSP/DevOps/freelancer managing multiple domains.
- Clear paid problem: reduce DNS incident detection/recovery time and provide audit evidence.
- Simple business model hypothesis.
- Post-hackathon roadmap.
- Architecture diagram.
- Security model.

## Acceptance criteria

A judge can answer in under 30 seconds:

- [ ] Who pays?
- [ ] What expensive/problematic event do they avoid?
- [ ] Why is DomainTwin better than manual DNS recovery?
- [ ] Why is name.com central?
- [ ] What becomes a SaaS after the hackathon?

**Winning impact:** Maximum for Feasibility.

---

# Gate 11 — Submission Quality

## Repository

- [ ] Clean README.
- [ ] Architecture diagram.
- [ ] Environment-variable reference.
- [ ] Setup instructions from clean clone.
- [ ] Test commands.
- [ ] Demo instructions.
- [ ] No secrets.

## Devpost project page

- [ ] Product name + one-line pitch.
- [ ] Real screenshots.
- [ ] Problem/solution written clearly.
- [ ] name.com integration explained endpoint-by-endpoint.
- [ ] Build story highlights progress during hackathon.
- [ ] Startup viability explained without hype.

## Demo video

Target approximately 3 minutes unless official challenge instructions require otherwise.

Required story:

```text
0:00 Problem
0:15 Healthy domain
0:25 Dangerous DNS mutation
0:35 CRITICAL incident
0:45 Exact diff
1:00 Evidence-based explanation
1:15 Rollback preview
1:30 name.com executes recovery
1:45 VERIFIED RECOVERY
2:00 Audit timeline
2:15 Emergency domain search
2:30 Availability + registration
2:45 DNS clone + verify
3:00 Closing one-line pitch
```

## Acceptance criteria

- [ ] No slide-only sections where live product can be shown.
- [ ] name.com API actions are visibly demonstrated.
- [ ] Core recovery succeeds deterministically on three consecutive rehearsals.
- [ ] Emergency flow succeeds deterministically on three consecutive rehearsals.
- [ ] Narration explains value, not implementation trivia.
- [ ] Final video is understandable without reading README.

**Winning impact:** Maximum — presentation.

---

# Gate 12 — Freeze

At freeze:

- No new features.
- Only blocker fixes.
- Demo dataset/scenario locked.
- Production/sandbox labels locked.
- Submission copy locked.

## Final acceptance checklist

DomainTwin is competition-ready only if all are true:

- [ ] Real name.com domain listing works.
- [ ] Real DNS read works.
- [ ] Real DNS mutation works.
- [ ] Known-good snapshots work.
- [ ] DNS diff works.
- [ ] Risk score is deterministic/explainable.
- [ ] Incident auto-detection works.
- [ ] AI explanation uses evidence only.
- [ ] Human-approved rollback works.
- [ ] Post-recovery verification works.
- [ ] Incident timeline works.
- [ ] Emergency search works.
- [ ] Availability check works.
- [ ] Emergency registration works in the controlled demo environment.
- [ ] DNS clone works.
- [ ] Clone verification works.
- [ ] Partial failures are represented honestly.
- [ ] Public `/demo` requires no account.
- [ ] Repo is reproducible from a clean clone.
- [ ] Demo rehearsed three times without manual data edits.
- [ ] Devpost submission explicitly maps DomainTwin to judging criteria.

---

# Internal competitive scorecard

This is an internal heuristic, not an official judging formula.

Score each 0–5 before submission:

| Dimension | Target |
|---|---:|
| Real problem clarity | 5 |
| name.com API depth | 5 |
| Originality | >=4 |
| Technical execution | >=4 |
| Demo WOW | 5 |
| Reliability | >=4 |
| Startup feasibility | >=4 |
| Visual polish | >=4 |
| Audit / safety credibility | >=4 |
| Build progress evidence | 5 |

**Submission rule:** do not spend time adding secondary features while any of API depth, core recovery reliability or demo clarity is below 4/5.

---

# Priority order from now

1. name.com Core API.
2. Snapshot + diff engine.
3. Risk + health + incidents.
4. Recovery engine.
5. Private UI wired to real backend.
6. AI explanation.
7. Emergency domain flow.
8. Edge cases/tests.
9. Optional authentication/signup only if all above are stable.
10. Submission polish and freeze.
