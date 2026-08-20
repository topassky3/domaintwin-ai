# Gate 10 — Startup / Feasibility Proof

## One-line business thesis

**DomainTwin is a domain-continuity control plane for teams that manage business-critical domains: it detects dangerous DNS drift, explains evidence, prepares an exact human-approved rollback, executes recovery through name.com, verifies the resulting DNS fingerprint, and preserves an audit trail.**

This document is a **business-model hypothesis for the hackathon**, not a claim of validated pricing or market traction.

---

## The 30-second judge test

A judge should be able to answer these five questions immediately.

### 1. Who pays?

Primary customer: **agencies, MSPs, DevOps/platform teams, and technical freelancers managing multiple customer or production domains**.

The strongest initial wedge is a small technical team responsible for roughly 10–250 domains where a DNS mistake can break websites, email, APIs, or customer-facing services.

### 2. What expensive/problematic event do they avoid?

They pay to reduce the operational impact of **DNS misconfiguration, accidental record deletion, unsafe changes, compromised credentials, provider-side race conditions, and recovery under incident pressure**.

The paid problem is not “DNS management.” The paid problem is **time-to-detect + time-to-recover + proof that recovery actually restored the intended state**.

### 3. Why is DomainTwin better than manual DNS recovery?

Manual recovery usually depends on a human remembering the previous state, reading change history, editing records one by one, and then deciding whether service is truly fixed.

DomainTwin adds a deterministic recovery boundary:

1. Immutable known-good DNS snapshot.
2. Deterministic Current → Known-Good diff.
3. Explainable risk score and incident evidence.
4. Exact CREATE / UPDATE / DELETE preview.
5. Explicit human approval before mutation.
6. Provider mutation through name.com.
7. Fresh provider read after mutation.
8. Expected-vs-actual fingerprint verification.
9. Ordered audit evidence.

The product therefore sells **verified continuity**, not merely another DNS editor.

### 4. Why is name.com central?

name.com is structurally required to the demonstrated product, not used as a decorative API call.

DomainTwin uses name.com for the operational domain lifecycle:

- list domains;
- read domain state;
- read DNS records;
- create DNS records;
- update DNS records;
- delete DNS records;
- search candidate emergency domains;
- check exact availability;
- register a controlled emergency domain in sandbox;
- read and clone DNS to the emergency domain;
- re-read destination DNS for verification.

Without the registrar/DNS control-plane API, DomainTwin could detect or explain incidents but could not complete the demonstrated **Detect → Restore → Prove** or **Search → Register → Clone → Verify** loops.

### 5. What becomes a SaaS after the hackathon?

The hackathon control plane becomes a multi-tenant continuity service with:

- scheduled monitoring;
- team workspaces;
- domain portfolios;
- incident alerting;
- recovery policies;
- human approvals;
- verified recovery history;
- emergency-domain continuity;
- audit/report exports;
- role-based access and billing.

---

# Target customer and buying trigger

## Initial ICP

**Small agency / MSP / platform team managing business-critical domains for multiple services or customers.**

Characteristics:

- 10–250 managed domains is a practical starting portfolio.
- DNS changes are infrequent enough to be risky but important enough to break production.
- More than one person may touch DNS over time.
- The team needs a recoverable known-good state rather than only provider change history.
- A customer-facing outage creates support load, reputation damage, SLA pressure, or lost transactions.

## Buying trigger

The most credible buying moments are:

- after a DNS outage or near miss;
- before handing DNS operations to a growing team;
- when an agency/MSP starts managing many customer zones;
- when compliance or customer requirements demand change evidence;
- when recovery is currently a runbook/manual screenshot process.

---

# Product wedge

## Wedge: verified DNS recovery

The first paid outcome is intentionally narrow:

> “When DNS changes unexpectedly, show me exactly what changed, let me approve the recovery, restore the known-good state, and prove that the provider now matches it.”

This is easier to understand and demonstrate than a broad “AI for domains” platform.

## Expansion: continuity control plane

Once the recovery wedge is trusted, DomainTwin expands naturally into:

- continuous drift monitoring;
- portfolio-wide risk;
- incident workflows;
- policy approvals;
- customer audit reports;
- emergency domain readiness;
- registrar/domain lifecycle automation.

---

# Business model hypothesis

Do not present these as validated prices. Gate 10 only needs a credible SaaS structure.

## Packaging hypothesis

### Starter

For freelancers/small teams with a small number of domains.

- continuous snapshots and drift monitoring;
- incident history;
- verified manual recovery;
- limited retention.

### Team

For agencies and DevOps/platform teams.

- larger domain portfolio;
- team approvals;
- longer audit retention;
- alerts/integrations;
- recovery policy controls.

### MSP

For providers managing many customer domains.

- portfolio/client segmentation;
- higher limits;
- customer-facing recovery reports;
- reusable policy templates;
- API/webhook automation.

## Revenue mechanism

**Recurring subscription with portfolio/domain limits**, with higher tiers charging for collaboration, retention, reporting, automation, and larger managed portfolios.

Emergency-domain continuity can become a higher-tier capability because it uses additional registrar lifecycle operations and has clear incident value.

The important economic property is recurring revenue for continuous protection, rather than charging only after an outage occurs.

---

# Why the product can be built from the hackathon artifact

Gate 10 does not depend on speculative infrastructure. The core SaaS primitives already exist in the repository:

- provider adapter/client;
- normalized DNS model;
- immutable snapshots and fingerprints;
- deterministic diff;
- risk engine;
- health observations;
- incident state and timeline;
- evidence-grounded AI explanation;
- recovery plans and ordered audit;
- emergency-domain plans and verification;
- server-side provider proxy;
- safe mutation flags and production boundaries;
- private product workspace.

The post-hackathon work is therefore primarily **multi-tenancy, scheduling, notifications, access control, billing, operational hardening, and onboarding**, not rebuilding the core recovery engine.

---

# Post-hackathon roadmap

## Phase 1 — Operable SaaS

- real account creation and authentication;
- organizations/workspaces;
- encrypted provider credential storage;
- scheduled DNS/health monitoring;
- email/Slack/webhook incident notifications;
- per-domain recovery policy;
- production deployment and observability;
- billing and domain/portfolio limits.

## Phase 2 — Team continuity workflows

- RBAC and approval roles;
- change windows;
- recovery reports;
- retention controls;
- incident export;
- portfolio dashboards;
- customer/MSP segmentation.

## Phase 3 — Continuity platform

- pre-built emergency-domain readiness policies;
- richer domain lifecycle automation;
- additional registrar adapters where commercially useful while keeping name.com first-class;
- policy-as-code and API access;
- integrations with deployment/incident-management systems.

---

# Feasibility risks and honest boundaries

## Risk: DNS is critical infrastructure

Mitigation: mutations remain behind explicit human approval, environment guards, provider re-reads, verification, and audit.

## Risk: provider APIs fail or race

Mitigation: Gate 9 explicitly covers 401, 429, timeout/5xx, stale previews, partial rollback, verification mismatch, and safe failure states.

## Risk: AI hallucination

Mitigation: AI receives structured evidence only, cannot mutate DNS, and the deterministic recovery path remains functional when AI is disabled/unavailable.

## Risk: production credentials

Mitigation: credentials stay server-side; browser traffic uses the DomainTwin proxy; production mutations require explicit configuration; emergency registration is sandbox-only in the hackathon implementation.

## Risk: multi-tenant SaaS is not implemented yet

This is intentionally a post-hackathon milestone. The current artifact proves the difficult domain-specific recovery workflow before adding generic SaaS plumbing.

---

# Judge-ready answer

> DomainTwin is for agencies, MSPs and DevOps teams managing business-critical domains. They pay to reduce DNS incident detection and recovery time and to get evidence that the intended state was actually restored. Instead of manually reconstructing DNS under pressure, DomainTwin keeps a known-good twin, calculates the exact rollback, requires human approval, executes through name.com, re-reads the provider and verifies the fingerprint. name.com is central because it powers the domain and DNS lifecycle, including the emergency-domain flow. After the hackathon, the same engine becomes a recurring multi-tenant SaaS with scheduled monitoring, team approvals, alerts, audit history and portfolio-based plans.
