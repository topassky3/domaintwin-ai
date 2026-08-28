# P5 — Monitoring Lite

P5 turns the existing deterministic DomainTwin monitor into a scheduler-friendly automatic worker for the hackathon. It deliberately reuses the same DNS diff, health, risk and incident pipeline already exercised by the manual `/evaluate/` endpoint.

## Scope

P5 adds:

- `core.monitoring.evaluate_domain_state()` as the single reusable evaluation pipeline.
- `core.monitoring.run_monitoring_cycle()` for one isolated pass over active managed domains.
- `python manage.py monitor_domaintwin` as a one-shot command suitable for cron or Windows Task Scheduler.
- `python manage.py monitor_domaintwin --loop` as an optional separate worker for the live demo.
- `DOMAIN_MONITOR_INTERVAL_SECONDS` with a 60-second default for loop mode.
- per-domain failure isolation and structured JSON cycle summaries.

P5 does **not** add Celery, Redis, Kafka, a scheduler database, a second incident engine, or a monitoring-specific evidence schema.

## Evaluation pipeline

Each successful check follows exactly one path:

```text
ManagedDomain
  ↓
active Organization
  ↓
active ProviderConnection(name.com)
  ↓
known-good snapshot
  ↓
read live DNS from name.com
  ↓
deterministic DNS diff + fingerprint
  ↓
HTTP/HTTPS health probe
  ↓
deterministic risk
  ↓
HEALTHY / DEGRADED / INCIDENT
  ↓
incident open/update/resolve
```

The HTTP `POST /api/monitor/domains/<domain>/evaluate/` endpoint uses the same `evaluate_domain_state()` service. Manual and automatic monitoring therefore cannot drift into two different decision engines.

## Fail-closed boundaries

A scheduled cycle never crosses the provider boundary when:

- the Organization is inactive;
- the ManagedDomain is inactive;
- the Organization does not have an active `name.com` ProviderConnection; or
- the domain has no known-good baseline.

Inactive organizations/domains are not candidates. Missing provider bindings and missing baselines are returned as explicit `SKIPPED` results. A provider or health failure for one domain becomes a `FAILED` result and does not abort monitoring of other domains or tenants.

Provider secrets remain P4 server-only environment values and are never included in the cycle result.

## Commands

Run one complete cycle:

```bash
python manage.py monitor_domaintwin
```

Limit a run:

```bash
python manage.py monitor_domaintwin --organization acme
python manage.py monitor_domaintwin --domain example.com --domain example.net
```

For a hackathon worker process:

```bash
python manage.py monitor_domaintwin --loop
```

Override the loop interval:

```bash
python manage.py monitor_domaintwin --loop --interval-seconds 30
```

Loop intervals below 10 seconds are rejected to avoid aggressive provider polling.

For deployment, prefer a one-shot invocation from the platform scheduler or cron. The Django web process never starts monitoring implicitly.

Example cron entry for a one-minute check:

```text
* * * * * cd /srv/domaintwin/backend && /srv/domaintwin/backend/.venv/bin/python manage.py monitor_domaintwin
```

## Cycle result

The command prints one JSON object per cycle. It contains only operational metadata:

- `checked`
- `healthy`
- `degraded`
- `incident`
- `skipped`
- `failed`
- per-domain organization/domain, state, risk, observation and incident identifiers

No provider credential is serialized.

## P5 acceptance criteria

P5 is closed when all of the following are true:

1. Manual and scheduled evaluation share one deterministic service.
2. Only active Organization + ManagedDomain roots are candidates.
3. Missing/inactive provider binding stops the cycle before constructing a name.com client.
4. Missing known-good baseline stops the cycle before provider work.
5. One domain failure cannot stop other domains from being evaluated.
6. Existing incident semantics remain unchanged: open, idempotent update and resolution continue through `correlate_incident()`.
7. One-shot command output is scheduler-friendly JSON.
8. Optional loop mode has an explicit minimum interval and runs outside the web process.
9. No schema/data migration or fingerprint algorithm change is introduced by P5.
10. P1–P4 contracts, backend regression, TypeScript and production build remain green.
