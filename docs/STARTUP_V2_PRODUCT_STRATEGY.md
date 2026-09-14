# DomainTwin — Startup V2 Product Strategy

## Product thesis

**DomainTwin is the verified recovery layer for DNS.**

It continuously preserves known-good DNS state, detects dangerous drift, explains the blast radius, prepares an exact rollback, requires human approval, executes through the connected provider, and independently proves that recovery succeeded.

The product is not another DNS host, registrar, dashboard, or generic AI assistant.

Core promise:

> **When DNS breaks, DomainTwin tells you exactly what changed, lets you safely undo it, and proves that the intended state is live again.**

Primary workflow:

```text
SNAPSHOT -> DETECT -> EXPLAIN -> PREVIEW -> APPROVE -> RESTORE -> VERIFY -> EVIDENCE
```

AI is optional and non-authoritative. Deterministic state, recovery, verification, and audit are the product.

---

## Initial ICP

Start narrow:

- agencies and MSPs managing 20–500 customer domains;
- small platform/DevOps teams responsible for business-critical DNS;
- teams where multiple people or vendors can change DNS;
- teams without mature DNS-as-code or dedicated DNS SRE practices.

Buying triggers:

- recent DNS outage or near miss;
- accidental deletion/change of A, CNAME, MX, NS, TXT, SPF, DKIM or DMARC-related records;
- customer pressure for change evidence;
- growth from one operator to a shared operations team;
- fear of making a bad recovery under incident pressure.

Do not target large enterprises first. Do not sell to every domain owner.

---

## Differentiation

### Native provider history

Provider audit logs and history can show what changed, but DomainTwin should win on:

- cross-provider normalization;
- known-good state independent of provider history;
- exact rollback preview;
- stale-plan protection;
- human approval;
- post-change verification;
- provider + authoritative/public DNS verification;
- incident evidence and recovery reports;
- MSP/client portfolio workflows.

### DNS-as-code tools

DNSControl and octoDNS are strong for teams that already operate DNS through GitOps. DomainTwin should not try to replace them.

DomainTwin is the safety and recovery layer for teams that:

- still make some changes through provider dashboards/APIs;
- inherit legacy DNS;
- manage many client accounts;
- need incident recovery rather than a new configuration language.

Longer term, DomainTwin can ingest Git/IaC desired state as an additional trusted baseline.

---

## MVP paid outcome

A customer connects a provider and gets, for every protected domain:

1. automatic DNS snapshots;
2. a manually markable known-good version;
3. deterministic drift detection;
4. severity/blast-radius classification;
5. email/webhook alert;
6. exact rollback preview;
7. approval gate;
8. provider mutation;
9. fresh provider re-read;
10. authoritative DNS verification;
11. recovery evidence/report.

The first commercial version does **not** need emergency-domain registration, broad domain lifecycle automation, autonomous AI remediation, a marketplace, or dozens of integrations.

---

## Provider order

1. **name.com** — preserve the proven hackathon integration.
2. **Cloudflare** — first commercial expansion because it is common among agencies and SMB infrastructure teams.
3. **AWS Route 53** — second commercial expansion for DevOps/platform teams.

Provider adapters must expose a canonical interface for:

- list zones/domains;
- read records;
- create/update/delete records;
- capability discovery;
- provider-specific safe error normalization.

---

## Verification model

A provider API success response is not enough to declare recovery.

DomainTwin should separate three states:

1. **Provider state restored** — fresh provider read matches target fingerprint.
2. **Authoritative state restored** — authoritative nameservers return the expected records.
3. **Observed propagation** — configured public resolvers return the expected records, with TTL-aware status.

Only the first state is required for immediate rollback completion. The second and third provide stronger proof and a propagation timeline.

This becomes a major product differentiator: DomainTwin does not merely mutate DNS; it proves recovery.

---

## Security and tenancy blockers before paid multi-tenant use

Current organization/membership primitives are a good start, but productization requires:

- every snapshot, incident, recovery plan, audit event, health observation and managed domain to be tenant-scoped by stable foreign keys, not only domain-name strings;
- explicit tenant authorization on every API path;
- encrypted per-organization provider credentials;
- provider credential rotation/revocation support;
- least-privilege token guidance;
- immutable security-sensitive audit events;
- idempotent mutation execution;
- secrets excluded from logs and AI prompts;
- recovery permissions separated from read/monitor permissions.

No paid multi-tenant launch before isolation tests prove that one organization cannot read or mutate another organization's domains.

---

## Product UX

The main dashboard should answer only four questions:

1. **Are my protected domains healthy?**
2. **What changed?**
3. **Can I safely restore the last trusted state?**
4. **Has recovery actually propagated?**

Avoid turning the UI into a generic DNS editor.

Primary pages:

- Portfolio
- Incidents
- Recovery
- Evidence
- Connections
- Team / approvals

---

## AI role

Keep AI subordinate to evidence.

AI may:

- summarize the incident;
- translate DNS changes into likely business impact;
- suggest which evidence to inspect;
- produce customer-facing incident summaries.

AI may not:

- invent current DNS state;
- choose the trusted baseline by itself;
- execute mutations;
- bypass approval;
- mark an incident recovered.

The brand can remain **DomainTwin**, while “AI” becomes a capability rather than the core category.

---

## Pricing hypothesis for validation

Do not optimize pricing before interviews.

Suggested paid-pilot structure:

- **Pilot:** USD 99/month, up to 50 protected domains, assisted onboarding.
- **Team:** hypothesis around USD 149–199/month, larger portfolio + team approvals + longer retention.
- **MSP:** hypothesis around USD 399+/month, client segmentation, reporting, larger limits and API/webhooks.

The first target is not maximum ARPU. The first target is proving that an agency/MSP will pay recurring money for verified DNS recovery.

---

## First validation milestone

Success is **not** another large feature set.

Success milestone:

- 5 interviews with agencies/MSPs/platform teams;
- 2 organizations connect real non-production or low-risk domains;
- 1 organization pays for a pilot;
- DomainTwin detects a controlled DNS drift and completes a verified rollback end-to-end.

If nobody will pay after seeing the verified rollback workflow, revisit the ICP/message before building more platform features.

---

## P0 engineering sequence

1. Tenant isolation audit and model migration.
2. Per-organization encrypted provider connection model.
3. Scheduler for snapshots/health checks.
4. Alert delivery (email + webhook first).
5. Authoritative DNS verification and TTL-aware propagation state.
6. Cloudflare read-only adapter.
7. Cloudflare guarded mutations + rollback verification.
8. Production onboarding flow.
9. Minimal billing/plan limits.
10. Paid pilot deployment.

Every step must preserve the existing fail-closed recovery model.

---

## Kill list

Until a paid pilot exists, do **not** prioritize:

- autonomous remediation;
- broad “AI agents” features;
- dozens of registrar integrations;
- emergency-domain purchase automation;
- domain search/marketplace features;
- generic observability dashboards;
- enterprise SSO;
- mobile apps;
- complex usage-based billing;
- redesigns that do not shorten time-to-value.

---

## One-line pitch

**DomainTwin is the undo button for business-critical DNS: detect dangerous changes, approve an exact rollback, restore through your provider, and prove the fix is really live.**
