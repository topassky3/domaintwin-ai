# DomainTwin AI — Devpost Submission Candidate

## Project name

DomainTwin AI

## One-line pitch

**Verified domain continuity: detect dangerous DNS changes, explain the evidence, restore a trusted configuration through name.com, and prove recovery.**

## The problem

A small DNS mistake can take a website, API or email path offline. During an incident, the hard part is not editing a record — it is knowing what changed, deciding what state was actually trusted, recovering without making the situation worse, and proving that the provider now matches the intended configuration.

Teams managing many domains often reconstruct this manually from memory, screenshots, tickets or old configuration notes. That is slow and uncertain precisely when the pressure is highest.

## What DomainTwin does

DomainTwin treats DNS as a recoverable digital twin.

It:

1. reads the live domain/DNS state from name.com;
2. stores immutable snapshots and explicitly trusted known-good versions;
3. calculates deterministic DNS differences and risk factors;
4. correlates dangerous drift with health evidence to create incidents;
5. optionally asks AI to explain only the structured evidence already present;
6. generates exact CREATE / UPDATE / DELETE rollback operations;
7. requires human approval before any provider mutation;
8. applies the recovery through name.com;
9. re-reads the live provider state;
10. declares `RECOVERED` only when the normalized expected and actual fingerprints match.

A second continuity flow handles the case where the primary domain cannot be safely restored in time: DomainTwin can search for an emergency domain, check exact availability, preview the clone, require approval, register it in the name.com sandbox, clone the selected DNS state and verify the destination fingerprint before declaring `READY`.

## Why name.com is central

The name.com API is the execution plane for both core product flows.

| Product action | name.com Core API |
|---|---|
| Test connectivity | `GET /core/v1/hello` |
| Read managed portfolio | `GET /core/v1/domains` |
| Read domain | `GET /core/v1/domains/{domain}` |
| Read DNS | `GET /core/v1/domains/{domain}/records` |
| Create DNS | `POST /core/v1/domains/{domain}/records` |
| Update DNS | `PUT /core/v1/domains/{domain}/records/{id}` |
| Delete DNS | `DELETE /core/v1/domains/{domain}/records/{id}` |
| Search emergency candidates | `POST /core/v1/domains:search` |
| Check exact availability | `POST /core/v1/domains:checkAvailability` |
| Register controlled emergency domain | `POST /core/v1/domains` + `X-Idempotency-Key` |

This is not an integration where the sponsor API is called once for decoration. DomainTwin cannot detect provider drift, execute recovery, register continuity infrastructure or prove the final state without name.com.

## The two live product stories

### 1. Detect → Explain → Restore → Prove

```text
Healthy
→ known-good snapshot
→ dangerous DNS change
→ CRITICAL incident
→ deterministic evidence
→ AI explanation
→ exact rollback preview
→ human approval
→ name.com mutation
→ provider re-read
→ fingerprint MATCH
→ RECOVERED
```

### 2. Search → Check → Register → Clone → Verify

```text
SEARCH
→ CHECK
→ PREVIEW
→ APPROVE
→ REGISTER
→ CLONE
→ VERIFY
→ READY
```

## Technical architecture

- **Frontend:** Next.js 16 + TypeScript.
- **Backend:** Django 5.2.
- **Provider integration:** name.com Core API through a server-side client.
- **Persistence:** Django models for snapshots, incidents, explanations, recovery plans, emergency plans and ordered audit events.
- **AI:** optional evidence-based explanation through an OpenAI-compatible provider; core monitoring/recovery works if AI is unavailable.
- **Verification:** deterministic DNS normalization + SHA-256-style fingerprint comparison in the application logic.

Browser traffic reaches DomainTwin through a server-side proxy. Provider credentials do not cross into browser payloads.

## Safety model

Domain operations are deliberately fail-closed.

- DNS mutation is disabled by default.
- Production mutation requires a second explicit opt-in.
- Domain registration has another explicit opt-in and is hard-blocked outside sandbox.
- Every recovery/registration flow requires explicit human approval.
- Plans are revalidated before execution; stale state stops the mutation.
- AI never executes provider operations.
- Partial failures remain `PARTIAL` / `FAILED` instead of being presented as success.
- `RECOVERED` / `READY` require a fresh provider read and exact fingerprint match.

## What we built during the hackathon

We progressed from a public product shell and health endpoint to a working name.com-backed control plane with:

- provider CRUD integration;
- immutable trusted snapshots;
- deterministic diff/risk engines;
- health monitoring and incident state;
- evidence-grounded AI explanation;
- human-approved verified rollback;
- a full private operator UI;
- emergency domain search/check/register/clone/verify;
- explicit edge-case handling for auth, rate limit, timeout/5xx, stale plans, races, partial recovery and AI outage;
- startup/feasibility material and reproducible verification contracts.

Current regression baseline: **90 backend tests**, plus Gate 7/8/9/10/11 frontend/static contracts.

## Challenges

### Safe provider mutation

A recovery product cannot earn trust if it can accidentally make the incident worse. We treated provider writes as a controlled state machine rather than a button: exact preview, human approval, stale-plan check, operation audit, fresh read and final verification.

### Idempotent emergency registration

Registration can time out after the provider has accepted the request. The emergency plan persists an idempotency key and can resume from `APPLYING` without blindly repeating registration.

### AI without black-box control

AI is useful for explaining evidence but unsafe as the authority that changes DNS. We separated deterministic risk/recovery from explanation so DomainTwin remains functional when AI is disabled or unavailable.

## What we learned

The strongest domain-continuity primitive is not “AI edits DNS.” It is **trusted state + deterministic change evidence + explicit human authority + provider verification**. AI becomes more useful when it is constrained to explain that evidence instead of replacing it.

We also learned that name.com can support much more than a basic registrar UI: domain search, availability, lifecycle operations and DNS execution combine into a credible continuity control plane.

## Startup feasibility

Target users are agencies, MSPs, DevOps/platform teams and technical freelancers responsible for multiple business-critical domains.

The business-model hypothesis is a recurring subscription by managed portfolio, with higher tiers for team approvals, longer audit retention, alerts, policy controls, reports and automation.

This is intentionally presented as a **hypothesis**, not validated pricing or traction.

Post-hackathon work would add the standard SaaS layer around the proven recovery core: organizations, encrypted per-customer credentials, scheduled workers, notifications, RBAC, billing, production deployment/observability and broader registrar adapters where useful.

## What's next

1. multi-tenant organizations and encrypted provider credentials;
2. scheduled monitoring and alert delivery;
3. RBAC / approval roles;
4. recovery reports and retention policies;
5. portfolio billing and limits;
6. policy-as-code / API automation;
7. additional registrar adapters while keeping name.com as the primary demonstrated integration.

## Judging alignment

### Progress

The submission contains a working end-to-end product, not only a concept or slide deck.

### Concept

The real-world problem is operational uncertainty during domain/DNS incidents. DomainTwin converts trusted provider state into a deterministic, auditable recovery process.

### Feasibility

The difficult domain-specific core already works. The remaining commercial work is recognizable SaaS infrastructure rather than a missing core invention.

### name.com challenge

DomainTwin demonstrates deep API usage across reads, DNS mutations, search, availability, registration and verification, with name.com structurally required for both demo flows.

## Final submission links

- Repository: `https://github.com/topassky3/domaintwin-ai`
- Demo video: `https://youtu.be/6PZ8M8ZfGcc`

A public live deployment is intentionally omitted from the hackathon submission; the working product is demonstrated through the recorded local/sandbox flow and public repository.
