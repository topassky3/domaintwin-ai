# Gate 5 — Recovery Engine verification

Gate 5 is DomainTwin's Golden Gate: turn a verified incident into a deterministic rollback preview, require explicit human approval, mutate name.com only after approval, and prove recovery against the immutable known-good snapshot.

## Safety invariants

- Preview is read-only.
- Approval is a separate explicit action and requires JSON `{ "approve": true }`.
- Apply refuses PREVIEW plans.
- Apply refuses stale plans when live DNS changed after preview.
- Production mutation must remain disabled.
- `RECOVERED` is emitted only after post-mutation fingerprint verification matches the target snapshot.
- A failed operation never becomes false success: status is `FAILED` or `PARTIAL`.
- Reapplying an already `RECOVERED` plan is idempotent and performs no new mutation.

## Recovery API

```text
GET/POST /api/recovery/domains/{domain}/plans/
GET      /api/recovery/plans/{plan_id}/
POST     /api/recovery/plans/{plan_id}/approve/
POST     /api/recovery/plans/{plan_id}/apply/
```

## Plan operations

DomainTwin computes Current -> Known-Good operations deterministically:

```text
UPDATE  live record exists but semantic value differs
CREATE  known-good record is missing live
DELETE  unexpected live record is absent from known-good
```

Execution order is deterministic and availability-oriented:

```text
UPDATE -> CREATE -> DELETE
```

Every operation contains exact before/after evidence and, for UPDATE/DELETE, the provider record id required by name.com.

## 1. Local verification

```powershell
cd C:\Users\felipe\Desktop\domaintwin-ai

git fetch origin
git switch agent/recovery-engine
git pull origin agent/recovery-engine

cd backend
.\.venv\Scripts\Activate.ps1

python manage.py makemigrations --check
python manage.py migrate
python manage.py check
python manage.py test core
```

Expected target: 50 tests total (34 inherited + 16 Gate 5 tests), all passing.

## 2. Start from safe configuration

Confirm without exposing tokens:

```powershell
Get-Content .env |
  Select-String "NAMECOM_ENVIRONMENT|NAMECOM_ALLOW_MUTATIONS|NAMECOM_ALLOW_PRODUCTION_MUTATIONS"
```

Safe state:

```text
NAMECOM_ENVIRONMENT=sandbox
NAMECOM_ALLOW_MUTATIONS=0
NAMECOM_ALLOW_PRODUCTION_MUTATIONS=0
```

Gate 4 left the sandbox known-good state as:

```text
Domain: domaintwin-gate1-20260818151419.com
Snapshot v3: KNOWN_GOOD
A www -> 203.0.113.10
Provider record id observed during Gate 4: 13364925
```

The provider id should be rediscovered/confirmed from the live API rather than blindly trusted.

## 3. Enable sandbox-only mutation for the controlled drill

Stop Django before changing `.env`.

```powershell
(Get-Content .env) `
  -replace '^NAMECOM_ALLOW_MUTATIONS=.*$', 'NAMECOM_ALLOW_MUTATIONS=1' |
  Set-Content .env

Get-Content .env |
  Select-String "NAMECOM_ENVIRONMENT|NAMECOM_ALLOW_MUTATIONS|NAMECOM_ALLOW_PRODUCTION_MUTATIONS"
```

Required:

```text
NAMECOM_ENVIRONMENT=sandbox
NAMECOM_ALLOW_MUTATIONS=1
NAMECOM_ALLOW_PRODUCTION_MUTATIONS=0
```

Restart Django:

```powershell
python manage.py runserver
```

Use a second PowerShell:

```powershell
$domain = "domaintwin-gate1-20260818151419.com"
$records = Invoke-RestMethod "http://127.0.0.1:8000/api/namecom/domains/$domain/records/"
$records | ConvertTo-Json -Depth 8
```

Find the A `www` record whose answer is `203.0.113.10` and save its id:

```powershell
$a = $records.records | Where-Object { $_.type -eq "A" -and $_.host -eq "www" } | Select-Object -First 1
$recordId = $a.id
$recordId
```

## 4. Create a real CRITICAL incident again

```powershell
$dangerBody = @{
    type   = "A"
    host   = "www"
    answer = "198.51.100.20"
    ttl    = 300
} | ConvertTo-Json

Invoke-RestMethod `
    -Method PUT `
    -Uri "http://127.0.0.1:8000/api/namecom/domains/$domain/records/$recordId/" `
    -ContentType "application/json" `
    -Body $dangerBody
```

Evaluate:

```powershell
$incidentEval = Invoke-RestMethod `
    -Method POST `
    -Uri "http://127.0.0.1:8000/api/monitor/domains/$domain/evaluate/"

$incidentEval | ConvertTo-Json -Depth 12
```

Expected core result (sandbox public health still fails):

```text
state = INCIDENT
driftDetected = true
MODIFIED = 1
unknownDestination = true
risk.score = 75
risk.severity = CRITICAL
incident.status = OPEN
```

Save the incident id:

```powershell
$incidentId = $incidentEval.incident.id
```

## 5. Generate rollback preview — MUST NOT mutate DNS

```powershell
$preview = Invoke-RestMethod `
    -Method POST `
    -Uri "http://127.0.0.1:8000/api/recovery/domains/$domain/plans/"

$preview | ConvertTo-Json -Depth 12
```

Expected:

```text
plan.status = PREVIEW
plan.requiresApproval = true
plan.canApply = false
plan.operationCount = 1
operations[0].action = UPDATE
operations[0].recordId = <live name.com id>
operations[0].before.answer = 198.51.100.20
operations[0].after.answer = 203.0.113.10
```

Save:

```powershell
$planId = $preview.plan.id
```

Prove preview was read-only:

```powershell
$stillDanger = Invoke-RestMethod "http://127.0.0.1:8000/api/namecom/domains/$domain/records/"
$stillDanger.records | Where-Object { $_.id -eq $recordId } | Format-List
```

The answer must still be `198.51.100.20`.

## 6. Prove apply is blocked without human approval

```powershell
try {
    Invoke-RestMethod `
      -Method POST `
      -Uri "http://127.0.0.1:8000/api/recovery/plans/$planId/apply/"
} catch {
    "HTTP $([int]$_.Exception.Response.StatusCode)"
    $_.ErrorDetails.Message
}
```

Expected HTTP 409 and message that explicit approval is required.

## 7. Explicit human approval

First prove `approve=false` is rejected:

```powershell
try {
    Invoke-RestMethod `
      -Method POST `
      -Uri "http://127.0.0.1:8000/api/recovery/plans/$planId/approve/" `
      -ContentType "application/json" `
      -Body (@{approve=$false} | ConvertTo-Json)
} catch {
    "HTTP $([int]$_.Exception.Response.StatusCode)"
    $_.ErrorDetails.Message
}
```

Then approve:

```powershell
$approved = Invoke-RestMethod `
    -Method POST `
    -Uri "http://127.0.0.1:8000/api/recovery/plans/$planId/approve/" `
    -ContentType "application/json" `
    -Body (@{approve=$true} | ConvertTo-Json)

$approved.plan | ConvertTo-Json -Depth 12
```

Expected:

```text
status = APPROVED
requiresApproval = false
canApply = true
```

## 8. Golden Gate — APPLY through name.com and VERIFY

```powershell
$applied = Invoke-RestMethod `
    -Method POST `
    -Uri "http://127.0.0.1:8000/api/recovery/plans/$planId/apply/"

$applied | ConvertTo-Json -Depth 14
```

Acceptance requires:

```text
plan.status = RECOVERED
operationResults[0].status = SUCCEEDED
verification.matched = true
verification.expectedFingerprint = verification.actualFingerprint
verification.actualRecords contains A www -> 203.0.113.10
```

The linked incident must be resolved as part of verified recovery.

## 9. Prove provider state and incident state

```powershell
$after = Invoke-RestMethod "http://127.0.0.1:8000/api/namecom/domains/$domain/records/"
$after.records | Where-Object { $_.id -eq $recordId } | Format-List
```

Answer must be `203.0.113.10`.

```powershell
$incident = Invoke-RestMethod "http://127.0.0.1:8000/api/incidents/$incidentId/"
$incident.incident.status
$incident.incident.timeline | Format-Table sequence,eventType
```

Expected final status `RESOLVED`, with recovery events appended after the incident events.

## 10. Prove idempotency

Capture audit length:

```powershell
$beforeReplay = Invoke-RestMethod "http://127.0.0.1:8000/api/recovery/plans/$planId/"
$auditCountBefore = $beforeReplay.plan.audit.Count
```

Call apply again:

```powershell
$replay = Invoke-RestMethod `
    -Method POST `
    -Uri "http://127.0.0.1:8000/api/recovery/plans/$planId/apply/"

$replay.plan.status
$replay.plan.audit.Count
$auditCountBefore
```

Expected:

```text
RECOVERED
same audit count as before replay
```

No new DNS mutation should occur.

## 11. Optional stale-plan safety proof

Covered by unit tests. The behavior is:

```text
preview created from live fingerprint X
live DNS changes to fingerprint Y
approve + apply old preview
=> HTTP 409
=> plan status STALE
=> zero recovery operations from the stale plan
```

For the live Golden Gate drill we do not intentionally introduce a second race because the successful recovery path is the primary demo.

## 12. Final security reset

Stop Django and return sandbox mutation to zero:

```powershell
cd C:\Users\felipe\Desktop\domaintwin-ai\backend

(Get-Content .env) `
  -replace '^NAMECOM_ALLOW_MUTATIONS=.*$', 'NAMECOM_ALLOW_MUTATIONS=0' |
  Set-Content .env

Get-Content .env |
  Select-String "NAMECOM_ENVIRONMENT|NAMECOM_ALLOW_MUTATIONS|NAMECOM_ALLOW_PRODUCTION_MUTATIONS"
```

Required final state:

```text
NAMECOM_ENVIRONMENT=sandbox
NAMECOM_ALLOW_MUTATIONS=0
NAMECOM_ALLOW_PRODUCTION_MUTATIONS=0
```

Final regression:

```powershell
python manage.py makemigrations --check
python manage.py check
python manage.py test core

cd ..
git status
git log -1 --oneline
```

## Gate 5 acceptance

Gate 5 passes only when:

- deterministic Current -> Known-Good preview is correct;
- UPDATE / CREATE / DELETE planning is unit-tested;
- preview performs zero mutation;
- apply before approval returns 409;
- approval requires literal `approve=true`;
- stale preview is rejected;
- real sandbox apply uses name.com mutation;
- each operation result is audited;
- partial/failed operations never return false success;
- verification compares semantic DNS fingerprints;
- `RECOVERED` appears only on exact verification match;
- linked incident becomes RESOLVED after verified recovery;
- replay of RECOVERED plan is idempotent;
- all 50 tests pass;
- mutation flags end at zero;
- working tree is clean.
