# Gate 1 — name.com Core Integration

Status: **IN PROGRESS**

This gate proves that name.com is structurally central to DomainTwin AI before work begins on snapshots, incident scoring, AI explanation, or recovery orchestration.

## Official environments

- Sandbox: `https://api.dev.name.com`
- Production: `https://api.name.com`
- API version: CORE v1
- Authentication: HTTP Basic with username + API token
- Sandbox username: normal name.com username with `-test` appended

DomainTwin appends `-test` automatically when `NAMECOM_ENVIRONMENT=sandbox` and the configured username does not already contain that suffix.

## Security defaults

DomainTwin never sends the name.com token to the frontend.

DNS mutations require:

```text
NAMECOM_ALLOW_MUTATIONS=1
```

Production mutations additionally require:

```text
NAMECOM_ALLOW_PRODUCTION_MUTATIONS=1
```

During the hackathon, keep production mutations disabled until the recovery workflow is explicitly ready for a controlled production demonstration.

## Backend endpoints implemented

```text
GET    /api/namecom/status/
GET    /api/namecom/domains/
GET    /api/namecom/domains/{domain}/
GET    /api/namecom/domains/{domain}/records/
POST   /api/namecom/domains/{domain}/records/
PUT    /api/namecom/domains/{domain}/records/{id}/
DELETE /api/namecom/domains/{domain}/records/{id}/
```

## Windows PowerShell — local setup

From the repository root, first preserve any generated/uncommitted frontend changes:

```powershell
git status
git stash push -u -m "local Next.js generated files before Gate 1"
git fetch origin --prune
git switch main
git pull --ff-only origin main
git switch -c agent/namecom-core --track origin/agent/namecom-core
```

Do not drop the stash yet.

### Backend dependencies

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Create local environment file

```powershell
Copy-Item .env.example .env
notepad .env
```

Fill only your real sandbox values locally:

```text
NAMECOM_ENVIRONMENT=sandbox
NAMECOM_USERNAME=YOUR_NORMAL_NAMECOM_USERNAME
NAMECOM_API_TOKEN=YOUR_SANDBOX_API_TOKEN
NAMECOM_TIMEOUT_SECONDS=10
NAMECOM_ALLOW_MUTATIONS=0
NAMECOM_ALLOW_PRODUCTION_MUTATIONS=0
```

Never paste the token into source code, screenshots, issues, PR descriptions, or chat logs.

## Read-only verification

Run tests first:

```powershell
python manage.py test core
python manage.py check
```

Start Django:

```powershell
python manage.py runserver
```

Then in another PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/namecom/status/
```

Expected shape:

```json
{
  "status": "connected",
  "provider": "name.com",
  "environment": "sandbox"
}
```

List sandbox domains:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/namecom/domains/
```

If the sandbox account has no domain yet, register a test domain in the sandbox before trying DNS CRUD.

## Controlled DNS CRUD test

Only after read-only connectivity passes, change locally:

```text
NAMECOM_ALLOW_MUTATIONS=1
```

Restart Django.

Use one sandbox domain returned by `/api/namecom/domains/` and replace `YOUR_SANDBOX_DOMAIN` below.

### List records

```powershell
$domain = "YOUR_SANDBOX_DOMAIN"
Invoke-RestMethod "http://127.0.0.1:8000/api/namecom/domains/$domain/records/"
```

### Create a harmless test TXT record

```powershell
$body = @{
  type = "TXT"
  host = "_domaintwin-gate1"
  answer = "gate1-ok"
  ttl = 300
} | ConvertTo-Json

$created = Invoke-RestMethod `
  -Method POST `
  -Uri "http://127.0.0.1:8000/api/namecom/domains/$domain/records/" `
  -ContentType "application/json" `
  -Body $body

$created
```

Capture the returned record id:

```powershell
$recordId = $created.record.id
$recordId
```

### Update the TXT record

```powershell
$body = @{
  type = "TXT"
  host = "_domaintwin-gate1"
  answer = "gate1-updated"
  ttl = 300
} | ConvertTo-Json

Invoke-RestMethod `
  -Method PUT `
  -Uri "http://127.0.0.1:8000/api/namecom/domains/$domain/records/$recordId/" `
  -ContentType "application/json" `
  -Body $body
```

### Verify the changed state

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/namecom/domains/$domain/records/"
```

### Delete the TXT record

```powershell
Invoke-RestMethod `
  -Method DELETE `
  -Uri "http://127.0.0.1:8000/api/namecom/domains/$domain/records/$recordId/"
```

Verify it no longer appears:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/namecom/domains/$domain/records/"
```

## Sandbox limitation

A successful DNS mutation in name.com sandbox proves API state changes, but sandbox DNS records do **not** resolve publicly. DomainTwin must therefore distinguish:

- API-state verification in sandbox
- public DNS / HTTP verification in a later controlled production demo or explicitly labeled simulation

Never claim that sandbox API records caused a real public DNS outage or recovery.

## Error handling acceptance

DomainTwin normalizes name.com failures into JSON containing:

```text
message
status
retryable
details
```

Rate limits and server/network failures are marked retryable where appropriate. Authentication and authorization failures are not silently retried.

## Gate 1 acceptance checklist

Gate 1 passes only when all are true:

- [ ] `GET /api/namecom/status/` connects to real name.com sandbox credentials.
- [ ] `/api/namecom/domains/` returns real sandbox API data.
- [ ] `/records/` returns real sandbox DNS state.
- [ ] DomainTwin creates the `_domaintwin-gate1` TXT record through name.com.
- [ ] DomainTwin updates that record.
- [ ] DomainTwin deletes that record.
- [ ] The post-delete list proves the record is gone.
- [ ] Unit tests pass.
- [ ] `python manage.py check` passes.
- [ ] API token is absent from browser payloads, server logs, git history and screenshots.
- [ ] Production DNS mutation remains disabled.

When every checkbox passes, merge Gate 1 and move to Gate 2: Digital Twin / Snapshot Engine.
