# DomainTwin AI

**Verified domain continuity for teams that cannot afford to guess during a DNS incident.**

DomainTwin detects dangerous DNS drift, preserves trusted known-good DNS snapshots, explains incident evidence, generates an exact rollback plan, requires human approval, executes recovery through the name.com API, and verifies the live provider state before declaring success.

Built for the **DevNetwork [API + Cloud + AI] Hackathon 2026**, targeting the **name.com Domain API Challenge**.

## Core product story

**Detect → Explain → Restore → Prove.**

```text
Healthy
→ known-good snapshot
→ dangerous DNS change
→ incident + deterministic risk
→ evidence-based AI explanation
→ exact rollback preview
→ human approval
→ name.com mutation
→ fresh provider read
→ fingerprint verification
→ RECOVERED
```

Second sponsor-depth flow:

```text
SEARCH
→ CHECK
→ PREVIEW
→ APPROVE
→ REGISTER
→ CLONE
→ VERIFY
→ READY
```

## What is implemented

- name.com sandbox/production client with explicit safety guards
- domain listing and DNS read/write operations
- immutable DNS snapshots and known-good versions
- deterministic DNS diff and risk scoring
- HTTP/HTTPS health checks and incident timelines
- evidence-based AI incident explanations with deterministic fallback
- human-approved rollback planning and execution
- post-recovery provider re-read and exact fingerprint verification
- emergency domain search, availability check, sandbox registration and DNS clone
- persistent recovery/emergency audit trails
- public guided demo at `/demo`
- public startup/feasibility proof at `/feasibility`
- private product workspace under `/app/*`
- Gate 7/8/9/10 contract checks and 90 backend regression tests

## Why name.com is central

name.com is the real execution plane, not a decorative API call.

| Capability | name.com Core API operation |
|---|---|
| Connectivity | `GET /core/v1/hello` |
| Portfolio | `GET /core/v1/domains` |
| Domain detail | `GET /core/v1/domains/{domain}` |
| DNS state | `GET /core/v1/domains/{domain}/records` |
| DNS create | `POST /core/v1/domains/{domain}/records` |
| DNS update | `PUT /core/v1/domains/{domain}/records/{id}` |
| DNS delete | `DELETE /core/v1/domains/{domain}/records/{id}` |
| Emergency search | `POST /core/v1/domains:search` |
| Exact availability | `POST /core/v1/domains:checkAvailability` |
| Sandbox registration | `POST /core/v1/domains` with `X-Idempotency-Key` |

Without provider reads, mutations and verification, DomainTwin cannot complete either of its two core flows.

## Architecture

```text
Browser / Next.js
       │
       │ /api/domaintwin/* server-side proxy
       ▼
Django control plane
 ├─ name.com client ───────────────► name.com Core API
 ├─ snapshot + diff engine
 ├─ deterministic risk engine
 ├─ health + incident engine
 ├─ recovery / emergency planners
 ├─ audit persistence
 └─ optional evidence-based AI ────► configured AI provider
```

Provider credentials remain server-side. The browser never receives the name.com API token.

See `docs/GATE10_ARCHITECTURE_SECURITY.md` for the detailed trust-boundary model.

## Safety model

Mutation is fail-closed and opt-in:

```text
NAMECOM_ALLOW_MUTATIONS=0
NAMECOM_ALLOW_PRODUCTION_MUTATIONS=0
NAMECOM_ALLOW_DOMAIN_REGISTRATION=0
AI_PROVIDER=disabled
```

Important boundaries:

- DNS mutation requires explicit server configuration.
- Production mutation requires a second explicit opt-in.
- Domain registration has an additional opt-in and is hard-blocked outside sandbox.
- Recovery/emergency execution requires explicit human approval.
- A stale plan is rejected before mutation.
- `RECOVERED` / `READY` require a fresh provider read and exact normalized DNS fingerprint match.
- AI explains evidence; it cannot execute DNS or registration operations.

## Repository structure

```text
domaintwin-ai/
├── backend/    # Django API, persistence, name.com integration and engines
├── frontend/   # Next.js + TypeScript public demo and product workspace
└── docs/       # Architecture, gates, verification and submission material
```

## Requirements

- Git
- Python 3.10+
- Node.js 20.9+
- npm
- name.com sandbox credentials for real provider integration
- optional OpenAI-compatible API key for AI explanation

## Clean-clone setup — Windows PowerShell

### 1. Clone

```powershell
git clone https://github.com/topassky3/domaintwin-ai.git
cd domaintwin-ai
git switch main
```

### 2. Backend

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py check
```

Edit `backend/.env` with your **sandbox** name.com username/token. Keep all mutation flags at `0` until a controlled demo step explicitly requires otherwise.

Run:

```powershell
python manage.py runserver
```

Backend health:

```text
http://127.0.0.1:8000/api/health/
```

### 3. Frontend

Open a second PowerShell:

```powershell
cd domaintwin-ai\frontend
Copy-Item .env.example .env.local
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

## Judge/demo routes

```text
/              public product landing
/demo          guided incident-recovery story
/feasibility   30-second startup/feasibility proof
/login         future SaaS access boundary
/app/overview  live control plane overview
/app/domains   name.com-backed domain portfolio
/app/incidents incident evidence + AI explanation
/app/recovery  recovery plans and audit
/app/emergency emergency domain continuity flow
```

## Verification commands

Backend:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python manage.py makemigrations --check --dry-run
python manage.py check
python manage.py test core
```

Expected current regression suite: **90 tests**.

Frontend:

```powershell
cd frontend
npm run gate7:contract
npm run gate8:contract
npm run gate9:contract
npm run gate10:contract
npm run gate11:contract
npm run typecheck
npm run build
```

## Safe demo procedure

Start with:

```text
NAMECOM_ENVIRONMENT=sandbox
NAMECOM_ALLOW_MUTATIONS=0
NAMECOM_ALLOW_PRODUCTION_MUTATIONS=0
NAMECOM_ALLOW_DOMAIN_REGISTRATION=0
AI_PROVIDER=disabled
```

Arm only the exact capability needed for the controlled demo, perform one approved operation, then return the flags to the safe defaults above.

Never demonstrate real production mutation for the hackathon.

See `docs/GATE11_REHEARSAL_RUNBOOK.md` for the controlled three-run rehearsal procedure.

## Submission material

- `docs/GATE11_SUBMISSION_QUALITY.md` — Gate 11 acceptance checklist
- `docs/DEVPOST_SUBMISSION.md` — project-page copy
- `docs/DEMO_VIDEO_SCRIPT.md` — approximately three-minute demo script
- `docs/GATE11_SCREENSHOTS.md` — real screenshot capture list
- `docs/GATE11_REHEARSAL_RUNBOOK.md` — deterministic rehearsal procedure
- `docs/HACKATHON_WINNING_PLAN.md` — original competition plan

## Business hypothesis

Target users are agencies, MSPs, DevOps/platform teams and technical freelancers responsible for multiple business-critical domains. The paid hypothesis is recurring protection by managed domain portfolio: monitoring, incident evidence, verified recovery, audit retention, collaboration and policy controls.

This is a **business-model hypothesis**, not a claim of validated pricing or traction.

## Current competition state

The core recovery and emergency-domain flows have already been demonstrated against the name.com sandbox with human approval and exact post-operation verification. Gate 11 focuses on reproducibility, rehearsals, screenshots, Devpost copy and video quality rather than adding new product features.
