# DomainTwin AI — Demo Video Script

Target duration: approximately **3 minutes** unless the final official challenge instructions require another limit.

Principle: show the live product whenever possible. Narration explains **value and proof**, not implementation trivia.

## Recording rules

- Record in **name.com sandbox** only.
- Start from safe flags and show `SANDBOX` visibly.
- Use the prepared demo domain/snapshot and do not improvise data during recording.
- Keep browser zoom and window size fixed.
- Hide terminals containing credentials.
- Never expose `.env`, tokens, Authorization headers or personal contact data.
- If a provider call needs waiting, trim dead time rather than replacing the live flow with slides.

## 0:00–0:15 — Problem

### Visual

Public landing or `/feasibility` headline, then immediately move into the live workspace.

### Narration

> A DNS mistake can take a website, API or email path offline. The difficult part is not editing a record — it is knowing exactly what changed, recovering the last trusted state safely, and proving the provider is correct again. DomainTwin turns that process into a verified recovery control plane.

## 0:15–0:25 — Healthy domain

### Visual

`/app/overview` or the selected domain page.

Show:

- SANDBOX
- name.com connected
- healthy/low-risk state
- known-good snapshot available

### Narration

> DomainTwin reads the real domain and DNS state through name.com and preserves an explicitly trusted known-good snapshot.

## 0:25–0:35 — Dangerous DNS mutation

### Visual

Controlled sandbox mutation prepared for the rehearsal. Show the changed A record, not credentials/terminal secrets.

### Narration

> Now a production-style A record drifts away from the trusted destination.

## 0:35–0:45 — CRITICAL incident

### Visual

Refresh/monitor until incident is visible.

Show:

- CRITICAL severity
- deterministic score
- active factors

### Narration

> DomainTwin compares the live provider state with the trusted twin, combines the DNS drift with health evidence, and creates a critical incident with deterministic factors.

## 0:45–1:00 — Exact diff

### Visual

Incident or DNS diff view.

Highlight before → after values.

### Narration

> Instead of a generic alert, the operator sees exactly what changed and the evidence that increased risk.

## 1:00–1:15 — Evidence-based explanation

### Visual

AI explanation card and cited evidence/timestamps.

### Narration

> AI is deliberately constrained to explanation. It receives structured incident evidence, distinguishes facts from probable cause, and cannot execute DNS changes. If AI is unavailable, recovery still works.

## 1:15–1:30 — Rollback preview

### Visual

Recovery preview with exact operations.

Show:

- target known-good snapshot
- CREATE / UPDATE / DELETE as applicable
- human approval boundary

### Narration

> DomainTwin generates the exact rollback from current state to known-good. Nothing changes until a human approves this plan.

## 1:30–1:45 — name.com executes recovery

### Visual

Approve once and apply the plan. Keep the name.com integration/provider status visible if possible.

### Narration

> After approval, DomainTwin executes the required DNS operation through the name.com Core API and records each provider result.

## 1:45–2:00 — VERIFIED RECOVERY

### Visual

Recovery result.

Show clearly:

- expected fingerprint
- actual fingerprint
- MATCH YES
- RECOVERED

### Narration

> Success is not assumed. DomainTwin re-reads name.com, normalizes the live DNS state, and declares recovered only when the expected and actual fingerprints match exactly.

## 2:00–2:15 — Audit timeline

### Visual

Ordered recovery/incident audit events.

### Narration

> The complete timeline remains auditable: detection, explanation, approval, provider mutation and independent verification.

## 2:15–2:30 — Emergency domain search

### Visual

`/app/emergency`.

Search a preselected fresh keyword.

### Narration

> If the primary domain cannot be safely restored in time, DomainTwin has a second continuity path. It searches real name.com candidates and checks exact availability.

## 2:30–2:45 — Availability + registration

### Visual

Show exact candidate, price/provider data supplied by sandbox, preview, explicit approval, then controlled sandbox registration.

### Narration

> The operator reviews the exact target and clone plan before registration. Registration has its own safety opt-in and is hard-blocked outside sandbox in this hackathon build.

## 2:45–2:57 — DNS clone + verify

### Visual

Show cloned DNS operation, provider re-read, expected == actual, `MATCH YES`, `READY`.

### Narration

> DomainTwin clones the trusted DNS records, re-reads the new domain from name.com, and marks it ready only after exact fingerprint verification.

## 2:57–3:05 — Close

### Visual

`/feasibility` judge-ready summary or landing headline.

### Narration

> DomainTwin AI is verified domain continuity: detect, explain, restore and prove — with name.com as the real execution plane.

If the final limit is a strict 3:00, shorten the audit segment and close by 2:59.

# Recording checklist

Before recording:

- [ ] Three consecutive core recovery rehearsals passed.
- [ ] Three consecutive emergency-domain rehearsals passed.
- [ ] Sandbox labels are visible.
- [ ] Safe reset performed before starting.
- [ ] Fresh emergency-domain candidate reserved for the recording.
- [ ] No secrets visible in tabs, terminal history or browser developer tools.
- [ ] Notifications/popups disabled.
- [ ] Narration practiced once with a timer.

After recording:

- [ ] Watch once with sound OFF: story remains understandable visually.
- [ ] Listen once without watching: narration explains problem/value clearly.
- [ ] Verify name.com actions are visible and understandable.
- [ ] Verify final `RECOVERED` and `READY / MATCH YES` are readable.
- [ ] Verify no secret or personal data appears in any frame.
