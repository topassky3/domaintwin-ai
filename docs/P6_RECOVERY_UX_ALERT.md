# P6 — Recovery UX + Alert

P6 closes the hackathon operator loop between automatic monitoring and verified recovery.

## Goal

When P5 detects a deterministic incident, the active tenant should immediately see an in-product alert and be able to move from evidence to the correct recovery workspace without searching manually.

P6 deliberately does **not** add email, Slack, PagerDuty, SMS, Celery, Redis, Kafka, or a notification queue. Those are post-hackathon delivery channels. The product already has the incident evidence needed for a strong live demo; P6 makes that evidence actionable.

## Flow

```text
P5 automatic monitoring
        ↓
OPEN Incident
        ↓
GET /api/alerts/
        ↓
Global product alert
        ↓
Evidence  |  Open recovery
                    ↓
         domain + incident deep link
                    ↓
DETECTED → PREVIEW → APPROVED → APPLY → VERIFIED
```

## Backend alert boundary

`GET /api/alerts/` reads persisted state only. It never constructs or calls the name.com provider client.

The endpoint:

- requires the normal authenticated private API boundary;
- resolves authorization from the active Membership;
- scopes incidents through active `ManagedDomain` ownership;
- includes only `OPEN` incidents;
- requires the incident baseline snapshot to belong to the exact same domain;
- excludes cross-tenant and corrupted evidence chains;
- orders alerts by severity and deterministic risk score;
- may expose the latest **consistent** recovery-plan summary for the incident;
- returns no credentials, provider token, or mutable provider object.

## Recovery UX

The global shell polls the lightweight alert endpoint every 15 seconds. This aligns with P5 dashboard refresh behavior without increasing name.com traffic because alerts are database-only reads.

An active alert links directly to:

```text
/app/incidents/<incident-id>
/app/recovery?domain=<domain>&incident=<incident-id>
```

The recovery page server-validates the query shape and passes the requested domain/incident context to the existing recovery workspace. The workspace still obtains all authoritative recovery state from protected backend APIs.

P6 adds a visible five-stage operator path:

1. `DETECTED`
2. `PREVIEW`
3. `APPROVED`
4. `APPLY`
5. `VERIFIED`

The existing backend approval, stale-plan guard, provider mutation guard, actor audit, and exact fingerprint verification remain the source of truth.

For plans with real DNS operations, the UI requires an additional explicit mutation acknowledgement before enabling `Apply approved recovery`. Verification-only plans do not require this acknowledgement because they do not mutate DNS.

## P6 acceptance criteria

- active alerts are tenant-scoped and non-disclosing;
- resolved incidents are not active alerts;
- corrupted baseline chains are excluded;
- alert reads never cross the provider boundary;
- a consistent latest recovery plan can be surfaced without accepting corrupted plan chains;
- the shell shows alert count and highest-priority alert globally;
- the shell refreshes alerts without additional provider polling;
- alert actions deep-link to evidence and the correct recovery domain;
- recovery presents an explicit deterministic progress path;
- real DNS mutation requires an extra UI acknowledgement in addition to backend approval;
- P1–P5 security and deterministic evidence contracts remain green;
- no schema or data migration is introduced;
- no external notification infrastructure is introduced.

## Deferred after the hackathon

- email/SMS/Slack/PagerDuty/Webhook delivery;
- alert acknowledgement/assignment tables;
- escalation policies and schedules;
- notification retries/dead-letter queues;
- per-user notification preferences.
