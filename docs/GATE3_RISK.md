# Gate 3 — Deterministic Risk Engine verification

This runbook verifies that DomainTwin turns Gate 2 DNS drift evidence into an auditable, deterministic risk score.

## Safety

Keep name.com mutations disabled during Gate 3 verification:

```env
NAMECOM_ENVIRONMENT=sandbox
NAMECOM_ALLOW_MUTATIONS=0
NAMECOM_ALLOW_PRODUCTION_MUTATIONS=0
```

Gate 3 is read-only. It consumes the known-good snapshot and live DNS state.

## Rules v1.0

| Rule | Points |
| --- | ---: |
| A/AAAA routing record changed | +30 |
| MX removed | +30 |
| NS modified | +35 |
| HTTP health failed | +30 |
| Unknown destination | +15 |
| TXT changed | +5 |

Scores are capped at 100.

Severity bands:

```text
0–24   LOW
25–49  MEDIUM
50–74  HIGH
75–100 CRITICAL
```

Every contribution is returned as a factor with its rule ID, points, reason, state, record type/host, and before/after evidence when applicable.

## 1. Update branch and run tests

```powershell
cd C:\Users\felipe\Desktop\domaintwin-ai
git fetch origin
git switch agent/deterministic-risk-engine
git pull origin agent/deterministic-risk-engine

cd backend
.\.venv\Scripts\Activate.ps1
python manage.py migrate
python manage.py check
python manage.py test core
```

Expected: no pending migration problems, no Django check issues, and 20 tests passing (12 inherited + 8 Gate 3 tests).

## 2. Start Django

```powershell
python manage.py runserver
```

Use another PowerShell window:

```powershell
$domain = "domaintwin-gate1-20260818151419.com"
```

## 3. Prove risk from real sandbox drift

Gate 2 left snapshot v2 as KNOWN_GOOD with one TXT record (`baseline-value`) while live sandbox DNS is empty. Therefore the current real diff is TXT REMOVED.

```powershell
$risk = Invoke-RestMethod `
  "http://127.0.0.1:8000/api/risk/domains/$domain/"

$risk | ConvertTo-Json -Depth 10
```

Expected core evidence:

```text
driftDetected = true
diffSummary.REMOVED = 1
risk.score = 5
risk.rawScore = 5
risk.severity = LOW
risk.factorCount = 1
risk.factors[0].ruleId = TXT_CHANGED
risk.factors[0].points = 5
risk.factors[0].before.answer = baseline-value
risk.factors[0].after = null
```

This proves the score is derived from the real name.com sandbox drift captured against the immutable known-good snapshot.

## 4. Prove deterministic output

Run the same evaluation twice:

```powershell
$riskA = Invoke-RestMethod `
  "http://127.0.0.1:8000/api/risk/domains/$domain/" | `
  ConvertTo-Json -Depth 10 -Compress

$riskB = Invoke-RestMethod `
  "http://127.0.0.1:8000/api/risk/domains/$domain/" | `
  ConvertTo-Json -Depth 10 -Compress

$riskA -eq $riskB
```

Expected:

```text
True
```

Same evidence must always produce the same score, severity and ordered factor list.

## 5. Exercise the Gate 4 integration seam

Gate 3 already accepts two explicit contextual signals that Gate 4 will later calculate automatically. These query values are a test seam only; they are not yet live health sensors.

```powershell
$contextRisk = Invoke-RestMethod `
  "http://127.0.0.1:8000/api/risk/domains/$domain/?http_health_failed=1&unknown_destination=1"

$contextRisk | ConvertTo-Json -Depth 10
```

With the current TXT removal, expected score:

```text
TXT_CHANGED           +5
HTTP_HEALTH_FAILED   +30
UNKNOWN_DESTINATION  +15
-------------------------
rawScore              50
score                 50
severity              HIGH
```

The response must expose all three factors; no hidden weighting is allowed.

## 6. Reject invalid context

```powershell
try {
  Invoke-RestMethod `
    "http://127.0.0.1:8000/api/risk/domains/$domain/?http_health_failed=maybe"
} catch {
  $_.ErrorDetails.Message
}
```

Expected HTTP 400 and a message explaining the accepted boolean values.

## 7. Final hygiene

```powershell
cd C:\Users\felipe\Desktop\domaintwin-ai\backend
python manage.py check
python manage.py test core

cd ..
git status
git log -1 --oneline
```

Also confirm without exposing any token:

```powershell
Get-Content backend\.env |
  Select-String "NAMECOM_ENVIRONMENT|NAMECOM_ALLOW_MUTATIONS|NAMECOM_ALLOW_PRODUCTION_MUTATIONS"
```

Expected:

```text
NAMECOM_ENVIRONMENT=sandbox
NAMECOM_ALLOW_MUTATIONS=0
NAMECOM_ALLOW_PRODUCTION_MUTATIONS=0
```

## Gate 3 acceptance

Gate 3 passes when:

- score is deterministic and capped at 100;
- severity boundaries are exact;
- every point contribution exposes a human-readable factor and evidence;
- repeated evaluation of identical evidence is identical;
- unit tests cover representative HIGH and CRITICAL cases;
- the real sandbox TXT removal produces a transparent LOW score of 5;
- contextual health/destination signals compose deterministically without AI;
- tests/checks pass and the working tree is clean.
