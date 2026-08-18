# Gate 4 — Health + Incident Detection verification

Gate 4 turns DomainTwin from a DNS diff/risk engine into an incident detector that correlates measured availability with deterministic DNS evidence.

## What Gate 4 adds

- safe public-domain HTTP health probe;
- safe public-domain HTTPS health probe;
- persisted `HealthObservation` records independent from incidents;
- measured unknown-destination derivation from changed A/AAAA/CNAME answers;
- deterministic monitor states: `HEALTHY`, `DEGRADED`, `INCIDENT`;
- persisted incident model with score, severity, factors and evidence;
- deterministic incident timeline;
- active-incident deduplication;
- automatic incident resolution when the triggering evidence clears;
- read APIs for monitor state and incident history.

## State policy

```text
No DNS drift + availability OK                         -> HEALTHY
Low DNS drift only OR availability failure only        -> DEGRADED
Dangerous DNS rule (A/AAAA, MX, NS)                    -> INCIDENT
DNS drift + availability failure                       -> INCIDENT
Risk score >= 50                                       -> INCIDENT
```

A health failure is persisted even if there is no incident. This keeps availability evidence independent from DNS evidence.

## Security

Health probes accept bare public domain names only. Direct IPs, localhost, URL paths/schemes and targets resolving to non-public IP addresses are blocked to reduce SSRF risk.

Keep name.com mutations disabled throughout Gate 4:

```env
NAMECOM_ENVIRONMENT=sandbox
NAMECOM_ALLOW_MUTATIONS=0
NAMECOM_ALLOW_PRODUCTION_MUTATIONS=0
DOMAIN_HEALTH_TIMEOUT_SECONDS=4
```

Gate 4 does not need DNS mutations.

## 1. Update branch

```powershell
cd C:\Users\felipe\Desktop\domaintwin-ai
git fetch origin
git switch agent/health-incident-detection
git pull origin agent/health-incident-detection

cd backend
.\.venv\Scripts\Activate.ps1
```

## 2. Migration and automated acceptance suite

```powershell
python manage.py makemigrations --check
python manage.py migrate
python manage.py check
python manage.py test core
```

Expected:

```text
No changes detected
Applying core.0002_health_incidents... OK
System check identified no issues
Found 34 test(s).
..................................
OK
```

The Gate 4 tests prove:

- valid/invalid health target handling;
- HTTP and HTTPS are measured independently;
- DNS resolution failure produces explicit failed probes;
- HEALTHY initial state;
- health-only DEGRADED state without incident;
- dangerous DNS change detection;
- unknown destination derivation;
- CRITICAL incident correlation;
- health evidence persists independently;
- same active evidence does not create duplicate incidents or duplicate timeline events;
- changed evidence updates the same incident;
- restored DNS + health automatically resolves the incident;
- timeline sequence is deterministic;
- status/list/detail APIs expose the same incident;
- missing KNOWN_GOOD baseline returns JSON 404.

## 3. Start Django

```powershell
python manage.py runserver
```

Use a second PowerShell window for API calls.

## 4. Real HTTP/HTTPS probe

This call does not use name.com; it exercises the real network health probe from your machine:

```powershell
$publicHealth = Invoke-RestMethod `
  "http://127.0.0.1:8000/api/monitor/domains/example.com/health/"

$publicHealth | ConvertTo-Json -Depth 10
```

On a normal Internet connection, at least one of HTTP/HTTPS should be healthy and `availabilityOk` should be true. If the local network blocks the request, keep the result as environment evidence and rely on the deterministic unit tests for the state-machine acceptance criterion.

Prove the SSRF guard:

```powershell
try {
  Invoke-RestMethod `
    "http://127.0.0.1:8000/api/monitor/domains/127.0.0.1/health/"
} catch {
  "HTTP $([int]$_.Exception.Response.StatusCode)"
  $_.ErrorDetails.Message
}
```

Expected: HTTP 400.

## 5. Real Gate 4 correlation against the existing name.com sandbox twin

Use the Gate 1/2 sandbox domain:

```powershell
$domain = "domaintwin-gate1-20260818151419.com"

$evaluation = Invoke-RestMethod `
  -Method POST `
  -Uri "http://127.0.0.1:8000/api/monitor/domains/$domain/evaluate/"

$evaluation | ConvertTo-Json -Depth 12
```

The local database already has snapshot v2 as `KNOWN_GOOD` with TXT `_domaintwin-gate2=baseline-value`, while the live sandbox DNS was left empty. Therefore the DNS evidence should still show a TXT `REMOVED` change.

Important sandbox limitation: name.com sandbox DNS is not intended to provide normal public DNS resolution. The health probe may therefore report a genuine resolution/availability failure for the sandbox domain. Do not present that limitation as a production outage; present it as sandbox evidence that the health channel is measured independently from the name.com API channel.

With the current local Gate 2 state, the likely result is:

```text
state                        INCIDENT
driftDetected                true
diff.summary.REMOVED         1
health.availabilityFailed    true
risk.score                   35
risk.severity                MEDIUM
incidentCreated              true
```

Risk composition:

```text
TXT_CHANGED                 +5
HTTP_HEALTH_FAILED         +30
-------------------------------
TOTAL                       35 MEDIUM
```

The incident opens because DNS drift and measured availability failure are correlated, even though the score itself is below HIGH.

## 6. Prove no duplicate active incident

Run the same evaluation again:

```powershell
$evaluation2 = Invoke-RestMethod `
  -Method POST `
  -Uri "http://127.0.0.1:8000/api/monitor/domains/$domain/evaluate/"

$evaluation2 | ConvertTo-Json -Depth 12
```

Expected:

```text
incidentCreated = false
same incident.id as first evaluation
```

If the relevant evidence signature is unchanged, the incident timeline should still have only the original three opening events.

## 7. Inspect monitor state and incident timeline

```powershell
$status = Invoke-RestMethod `
  "http://127.0.0.1:8000/api/monitor/domains/$domain/status/"
$status | ConvertTo-Json -Depth 10

$incidents = Invoke-RestMethod `
  "http://127.0.0.1:8000/api/incidents/domains/$domain/"
$incidents | ConvertTo-Json -Depth 10

$incidentId = $evaluation.incident.id
$detail = Invoke-RestMethod `
  "http://127.0.0.1:8000/api/incidents/$incidentId/"
$detail | ConvertTo-Json -Depth 12
```

Expected opening timeline order:

```text
1 DNS_EVIDENCE_CAPTURED
2 HEALTH_EVIDENCE_CAPTURED
3 INCIDENT_OPENED
```

Each incident exposes:

- opened/last-seen/resolved timestamps;
- score and severity;
- deterministic risk factors;
- baseline snapshot identity;
- current live fingerprint;
- DNS before/after diff;
- health observation and protocol evidence;
- unknown-destination flag;
- ordered timeline.

## 8. Final hygiene

Stop the development server and run:

```powershell
cd C:\Users\felipe\Desktop\domaintwin-ai\backend
python manage.py makemigrations --check
python manage.py check
python manage.py test core

Get-Content .env |
  Select-String "NAMECOM_ENVIRONMENT|NAMECOM_ALLOW_MUTATIONS|NAMECOM_ALLOW_PRODUCTION_MUTATIONS|DOMAIN_HEALTH_TIMEOUT_SECONDS"

cd ..
git status
git log -1 --oneline
```

Acceptance requires:

```text
NAMECOM_ENVIRONMENT=sandbox
NAMECOM_ALLOW_MUTATIONS=0
NAMECOM_ALLOW_PRODUCTION_MUTATIONS=0
34/34 tests pass
working tree clean
```

## Gate 4 acceptance mapping

- Domain starts HEALTHY -> automated integration test.
- Controlled dangerous DNS change detected -> automated A-record change test.
- Health failure recorded independently -> automated health-only DEGRADED test + `HealthObservation` persistence.
- Relevant drift/failure creates incident automatically -> automated CRITICAL test + real sandbox correlation.
- Incident contains timestamps, score, factors and evidence -> model/API assertions.
- Timeline ordering deterministic and understandable -> fixed sequence assertions and detail API.
- Re-running checks does not duplicate incidents -> repeated evaluation assertion + real sandbox rerun.

Gate 4 is complete only after the full automated suite and local real-network/sandbox verification are reviewed before merge.
