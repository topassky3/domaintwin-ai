# Gate 4 — Live name.com sandbox incident drill

Run this only after the automated Gate 4 suite passes.

This drill creates a controlled A-record baseline in name.com sandbox, captures it as KNOWN_GOOD, changes it to a different destination, verifies a CRITICAL incident, proves deduplication, restores the original A record, verifies automatic incident resolution, and finally disables mutations again.

The addresses `203.0.113.10` and `198.51.100.20` are documentation-only example addresses used solely as sandbox record values.

## Safety precondition

Production mutations must stay disabled:

```env
NAMECOM_ENVIRONMENT=sandbox
NAMECOM_ALLOW_PRODUCTION_MUTATIONS=0
```

Temporarily set:

```env
NAMECOM_ALLOW_MUTATIONS=1
```

Restart Django after changing `.env`.

## 1. Create a controlled known-good A record

```powershell
$domain = "domaintwin-gate1-20260818151419.com"

$baselineBody = @{
  type   = "A"
  host   = "www"
  answer = "203.0.113.10"
  ttl    = 300
} | ConvertTo-Json

$createdA = Invoke-RestMethod `
  -Method POST `
  -Uri "http://127.0.0.1:8000/api/namecom/domains/$domain/records/" `
  -ContentType "application/json" `
  -Body $baselineBody

$recordId = $createdA.record.id
$createdA | ConvertTo-Json -Depth 8
```

## 2. Capture the new known-good snapshot

```powershell
$v3 = Invoke-RestMethod `
  -Method POST `
  -Uri "http://127.0.0.1:8000/api/twin/domains/$domain/snapshots/"

$snapshot3 = $v3.snapshot.id
$v3.snapshot | ConvertTo-Json -Depth 8

Invoke-RestMethod `
  -Method POST `
  -Uri "http://127.0.0.1:8000/api/twin/domains/$domain/snapshots/$snapshot3/known-good/"
```

Expected: the snapshot contains `A www 203.0.113.10` and becomes KNOWN_GOOD.

## 3. Evaluate the baseline

```powershell
$baselineEval = Invoke-RestMethod `
  -Method POST `
  -Uri "http://127.0.0.1:8000/api/monitor/domains/$domain/evaluate/"

$baselineEval | ConvertTo-Json -Depth 12
```

DNS must show zero drift. Because name.com sandbox DNS is not normal public DNS, HTTP/HTTPS may fail resolution. If that happens, state should be `DEGRADED`, risk 30, and no incident should open because health failure is independent and DNS matches KNOWN_GOOD.

## 4. Create the dangerous DNS change

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

Expected if sandbox public resolution fails as usual:

```text
state                       INCIDENT
driftDetected               true
diff.summary.MODIFIED       1
unknownDestination          true
risk.score                  75
risk.severity               CRITICAL
incidentCreated             true
```

Expected transparent score:

```text
ADDRESS_RECORD_CHANGED     +30
HTTP_HEALTH_FAILED         +30
UNKNOWN_DESTINATION        +15
-------------------------------
TOTAL                       75 CRITICAL
```

Save the incident ID:

```powershell
$incidentId = $incidentEval.incident.id
```

## 5. Prove active-event deduplication

```powershell
$repeatEval = Invoke-RestMethod `
  -Method POST `
  -Uri "http://127.0.0.1:8000/api/monitor/domains/$domain/evaluate/"

$repeatEval.incidentCreated
$repeatEval.incident.id
$incidentId
```

Expected:

```text
False
same incident ID
```

Inspect timeline:

```powershell
Invoke-RestMethod `
  "http://127.0.0.1:8000/api/incidents/$incidentId/" | `
  ConvertTo-Json -Depth 12
```

If evidence is unchanged, opening timeline remains:

```text
1 DNS_EVIDENCE_CAPTURED
2 HEALTH_EVIDENCE_CAPTURED
3 INCIDENT_OPENED
```

## 6. Restore the known-good A record manually for Gate 4 verification

Gate 5 will later automate this exact restoration. For Gate 4 we restore it manually through the already verified name.com API integration.

```powershell
Invoke-RestMethod `
  -Method PUT `
  -Uri "http://127.0.0.1:8000/api/namecom/domains/$domain/records/$recordId/" `
  -ContentType "application/json" `
  -Body $baselineBody
```

Evaluate again:

```powershell
$recoveredEval = Invoke-RestMethod `
  -Method POST `
  -Uri "http://127.0.0.1:8000/api/monitor/domains/$domain/evaluate/"

$recoveredEval | ConvertTo-Json -Depth 12
```

Expected:

```text
driftDetected = false
incident.status = RESOLVED
```

If sandbox health still cannot resolve publicly, overall state can correctly remain `DEGRADED` because health failure is independent from the resolved DNS incident.

Timeline should now end with:

```text
INCIDENT_RESOLVED
```

## 7. Disable mutations immediately

Restore:

```env
NAMECOM_ALLOW_MUTATIONS=0
NAMECOM_ALLOW_PRODUCTION_MUTATIONS=0
```

Restart Django and confirm:

```powershell
Get-Content .env |
  Select-String "NAMECOM_ENVIRONMENT|NAMECOM_ALLOW_MUTATIONS|NAMECOM_ALLOW_PRODUCTION_MUTATIONS"
```

Expected:

```text
NAMECOM_ENVIRONMENT=sandbox
NAMECOM_ALLOW_MUTATIONS=0
NAMECOM_ALLOW_PRODUCTION_MUTATIONS=0
```

The live DNS should remain on the known-good A record `www -> 203.0.113.10`, which is useful as the starting baseline for Gate 5 recovery testing.
