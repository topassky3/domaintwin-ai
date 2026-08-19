# Gate 6 — Evidence-Based AI Incident Explanation

Gate 6 adds an AI analyst on top of DomainTwin's deterministic evidence. AI never owns risk scoring, incident creation, DNS mutation, recovery planning, approval, or verification.

## Input contract

Only these deterministic categories are provided to the model:

```text
previous_state
current_state
dns_diff
health_checks
risk_score
timestamps
```

The server also generates an evidence catalog with immutable IDs such as:

```text
DNS-001
HEALTH-DNS
HEALTH-HTTP
HEALTH-HTTPS
RISK-001
RISK-SCORE
TIME-OPENED
```

The model may only return references to those IDs. DomainTwin resolves the references back to deterministic facts before returning them to the UI.

## Output contract

```text
probable_cause
affected_service
evidence_refs
recommended_action
confidence
```

Facts and inference are deliberately separated:

- `evidence` is server-resolved deterministic evidence.
- `probableCause` is explicitly AI inference.
- `confidence` explains uncertainty.
- `recommendedAction` is advisory only.

## Safety invariants

- Prompt explicitly forbids invented DNS changes, outages, timestamps, attacks, recovery results and provider actions.
- DNS values are treated as untrusted data, never instructions.
- AI cannot call name.com or recovery mutation functions.
- AI cannot CREATE / UPDATE / DELETE / REGISTER.
- Human approval remains mandatory in the deterministic Recovery Engine.
- Unknown evidence references cause provider output to be marked `INVALID`.
- Missing key, timeout, provider outage or disabled AI yields `UNAVAILABLE` plus deterministic evidence.
- Detection, risk, incidents and recovery continue operating when AI is unavailable.
- Generated explanations are cached by incident evidence fingerprint + provider + model to avoid duplicate spend.

## Environment

Default safe configuration:

```env
AI_PROVIDER=disabled
AI_MODEL=gpt-5-mini
OPENAI_API_KEY=
AI_API_BASE_URL=https://api.openai.com/v1
AI_TIMEOUT_SECONDS=15
AI_MAX_OUTPUT_TOKENS=700
```

`gpt-5-mini` is used as the default API model because it is a cost-efficient OpenAI model suitable for well-defined structured tasks. The model remains configurable through `AI_MODEL`.

Do not commit or paste API keys into chat, logs, screenshots or the repository.

## API

```text
GET  /api/ai/incidents/{incident_id}/explanation/
POST /api/ai/incidents/{incident_id}/explanation/
POST /api/ai/incidents/{incident_id}/explanation/?force=1
```

GET before generation is read-only and returns `NOT_GENERATED` plus the exact input contract.

POST generates or retries. Successful generated output is cached. `force=1` intentionally regenerates the same evidence and should be used sparingly.

## Local verification

From repository root:

```powershell
cd C:\Users\felipe\Desktop\domaintwin-ai
git fetch origin
git switch agent/ai-incident-explanation
git pull origin agent/ai-incident-explanation

cd backend
.\.venv\Scripts\Activate.ps1
python manage.py makemigrations --check
python manage.py migrate
python manage.py check
python manage.py test core
```

Expected complete suite:

```text
Found 69 test(s).
.....................................................................
OK
```

Migration should apply `core.0004_incident_explanations` on the first run.

## Degraded-mode verification — no AI key required

Keep:

```env
AI_PROVIDER=disabled
NAMECOM_ALLOW_MUTATIONS=0
NAMECOM_ALLOW_PRODUCTION_MUTATIONS=0
```

Run Django:

```powershell
python manage.py runserver
```

In another PowerShell:

```powershell
$domain = "domaintwin-gate1-20260818151419.com"
$incidents = Invoke-RestMethod "http://127.0.0.1:8000/api/incidents/domains/$domain/"
$incidentId = $incidents.incidents[0].id
$incidentId
```

Read the AI contract without generation:

```powershell
$before = Invoke-RestMethod "http://127.0.0.1:8000/api/ai/incidents/$incidentId/explanation/"
$before | ConvertTo-Json -Depth 12
```

Before any explanation exists, expect:

```text
status = NOT_GENERATED
aiAvailable = false
probableCause = null
inputContract = previous_state/current_state/dns_diff/health_checks/risk_score/timestamps
```

Then POST while AI is disabled:

```powershell
$fallback = Invoke-RestMethod -Method POST "http://127.0.0.1:8000/api/ai/incidents/$incidentId/explanation/"
$fallback | ConvertTo-Json -Depth 12
```

Expect:

```text
status = UNAVAILABLE
aiAvailable = false
probableCause = "AI analysis unavailable; no probable cause was generated."
evidence = deterministic evidence remains present
safety.aiCanMutateDns = false
safety.humanApprovalStillRequired = true
```

This is an acceptance condition, not a failure: core DomainTwin functionality remains independent from AI.

## Live OpenAI verification

This step requires an OpenAI API key with API billing/access. ChatGPT subscription credentials are not used by the backend.

Stop Django, edit only local `backend/.env`, and configure:

```env
AI_PROVIDER=openai
AI_MODEL=gpt-5-mini
OPENAI_API_KEY=<local secret>
```

Never paste the key into chat.

Restart Django:

```powershell
python manage.py runserver
```

Then:

```powershell
$analysis = Invoke-RestMethod -Method POST "http://127.0.0.1:8000/api/ai/incidents/$incidentId/explanation/"
$analysis.analysis | ConvertTo-Json -Depth 12
```

Acceptance requires:

```text
status = GENERATED
aiAvailable = true
label = Evidence-based AI analysis
provider = openai
probableCause != null
affectedService in DNS/WEB/EMAIL/NAMESERVERS/MULTIPLE/UNKNOWN
evidenceRefs contains only IDs present in evidence
recommendedAction != null
confidence.level in LOW/MEDIUM/HIGH
safety.aiCanMutateDns = false
safety.humanApprovalStillRequired = true
```

The exact wording is not an acceptance condition. Evidence grounding is.

## Cache verification

Immediately GET the same incident:

```powershell
$cached = Invoke-RestMethod "http://127.0.0.1:8000/api/ai/incidents/$incidentId/explanation/"
$cached.analysis.cached
$cached.analysis.requestId
```

Expect:

```text
True
```

Then POST again without `force=1`:

```powershell
$again = Invoke-RestMethod -Method POST "http://127.0.0.1:8000/api/ai/incidents/$incidentId/explanation/"
$again.analysis.cached
$again.analysis.requestId
```

Expect `True` and the same request id: no new provider call should be made for unchanged evidence.

## Final safe state

After live verification, stop Django and return AI to disabled unless actively testing the UI:

```env
AI_PROVIDER=disabled
NAMECOM_ALLOW_MUTATIONS=0
NAMECOM_ALLOW_PRODUCTION_MUTATIONS=0
```

Final commands:

```powershell
python manage.py makemigrations --check
python manage.py migrate
python manage.py check
python manage.py test core

cd ..
git status
git log -1 --oneline
```

Gate 6 passes when:

- 69/69 tests pass;
- input contains only approved structured categories;
- deterministic evidence IDs are enforced;
- fake/invalid evidence refs are rejected;
- AI unavailable mode is explicit and non-blocking;
- a real provider explanation is evidence-grounded when API access is available;
- generated explanation is cached for unchanged evidence;
- AI has no mutation path;
- final name.com mutation flags remain zero;
- working tree is clean.
