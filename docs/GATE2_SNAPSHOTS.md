# Gate 2 — Digital Twin / Snapshot Engine verification

This runbook validates the Digital Twin against the real name.com sandbox domain created during Gate 1.

## Safety

Keep:

```env
NAMECOM_ENVIRONMENT=sandbox
NAMECOM_ALLOW_PRODUCTION_MUTATIONS=0
```

Enable `NAMECOM_ALLOW_MUTATIONS=1` only while running the controlled sandbox drift test. Restore it to `0` afterward.

## 1. Update and migrate

```powershell
cd C:\Users\felipe\Desktop\domaintwin-ai
git fetch origin
git switch agent/digital-twin-snapshots
git pull origin agent/digital-twin-snapshots

cd backend
.\.venv\Scripts\Activate.ps1
python manage.py migrate
python manage.py check
python manage.py test core
```

Acceptance: migrations apply, system check has no issues, and all tests pass.

## 2. Start Django

```powershell
python manage.py runserver
```

Use another PowerShell window for API calls.

```powershell
$domain = "domaintwin-gate1-20260818151419.com"
```

## 3. Capture empty baseline snapshot

Gate 1 left the sandbox DNS list empty.

```powershell
$baseline = Invoke-RestMethod `
  -Method POST `
  -Uri "http://127.0.0.1:8000/api/twin/domains/$domain/snapshots/"

$baseline.snapshot | Format-List
$snapshot1 = $baseline.snapshot.id
```

Expected: version `1`, recordCount `0`, and a 64-character fingerprint.

Mark it known-good:

```powershell
Invoke-RestMethod `
  -Method POST `
  -Uri "http://127.0.0.1:8000/api/twin/domains/$domain/snapshots/$snapshot1/known-good/"
```

Verify no drift:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/twin/domains/$domain/diff/" | ConvertTo-Json -Depth 8
```

Expected: `driftDetected=false` and all ADDED/REMOVED/MODIFIED counts equal zero.

## 4. Prove ADDED

Temporarily set `NAMECOM_ALLOW_MUTATIONS=1` in `backend/.env` and restart Django.

```powershell
$body = @{
  type = "TXT"
  host = "_domaintwin-gate2"
  answer = "baseline-value"
  ttl = 300
} | ConvertTo-Json

$created = Invoke-RestMethod `
  -Method POST `
  -Uri "http://127.0.0.1:8000/api/namecom/domains/$domain/records/" `
  -ContentType "application/json" `
  -Body $body

$recordId = $created.record.id
$created
```

Now:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/twin/domains/$domain/diff/" | ConvertTo-Json -Depth 8
```

Expected: `driftDetected=true`, `ADDED=1`.

## 5. Capture version 2 and make it KNOWN_GOOD

```powershell
$v2 = Invoke-RestMethod `
  -Method POST `
  -Uri "http://127.0.0.1:8000/api/twin/domains/$domain/snapshots/"

$snapshot2 = $v2.snapshot.id
$v2.snapshot | Format-List

Invoke-RestMethod `
  -Method POST `
  -Uri "http://127.0.0.1:8000/api/twin/domains/$domain/snapshots/$snapshot2/known-good/"
```

Expected: version `2`, recordCount `1`. Snapshot 1 remains unchanged.

## 6. Prove MODIFIED

```powershell
$updateBody = @{
  type = "TXT"
  host = "_domaintwin-gate2"
  answer = "changed-value"
  ttl = 300
} | ConvertTo-Json

Invoke-RestMethod `
  -Method PUT `
  -Uri "http://127.0.0.1:8000/api/namecom/domains/$domain/records/$recordId/" `
  -ContentType "application/json" `
  -Body $updateBody

Invoke-RestMethod "http://127.0.0.1:8000/api/twin/domains/$domain/diff/" | ConvertTo-Json -Depth 8
```

Expected: `MODIFIED=1` with before=`baseline-value` and after=`changed-value`.

## 7. Prove REMOVED

```powershell
Invoke-RestMethod `
  -Method DELETE `
  -Uri "http://127.0.0.1:8000/api/namecom/domains/$domain/records/$recordId/"

Invoke-RestMethod "http://127.0.0.1:8000/api/twin/domains/$domain/diff/" | ConvertTo-Json -Depth 8
```

Expected: `REMOVED=1` with the previous record preserved under `before`.

## 8. Prove snapshot immutability and version history

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/twin/domains/$domain/snapshots/" | ConvertTo-Json -Depth 8
Invoke-RestMethod "http://127.0.0.1:8000/api/twin/domains/$domain/snapshots/$snapshot2/" | ConvertTo-Json -Depth 8
```

Snapshot 2 must still contain `baseline-value` even though live DNS was changed and then deleted.

## 9. Restore safety

Set:

```env
NAMECOM_ALLOW_MUTATIONS=0
NAMECOM_ALLOW_PRODUCTION_MUTATIONS=0
```

Restart Django and run:

```powershell
python manage.py test core
python manage.py check
```

## Gate 2 acceptance

Gate 2 passes only when we have local evidence for:

- live DNS captured as an immutable versioned snapshot;
- explicit KNOWN_GOOD marker;
- zero-drift baseline;
- ADDED detection;
- MODIFIED detection with before/after;
- REMOVED detection with before/after;
- snapshot history unchanged after live DNS mutation;
- unit tests and Django checks passing.
