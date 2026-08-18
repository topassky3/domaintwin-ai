# DomainTwin AI

**Detect dangerous DNS changes, explain what broke, and restore a known-good Internet configuration in one click.**

Built for the DevNetwork [API + Cloud + AI] Hackathon 2026, with the name.com Domain API as the primary infrastructure integration.

## Current milestone

This branch contains the first public product surface and the local application foundation:

- Next.js public landing page
- `/login` placeholder for the future private workspace
- Django 5.2 backend
- `GET /api/health/`
- public landing runtime API status

The authenticated DNS operations, snapshots, incident engine, recovery engine and name.com integration are intentionally deferred to later milestones.

## Repository structure

```text
domaintwin-ai/
├── frontend/   # Next.js + TypeScript public/private web application
├── backend/    # Django API
└── docs/       # Hackathon and architecture documentation
```

## Requirements

- Node.js 20.9 or newer
- npm
- Python 3.10 or newer
- Git

## Run locally on Windows PowerShell

Clone the repository and switch to the implementation branch:

```powershell
git clone https://github.com/topassky3/domaintwin-ai.git
cd domaintwin-ai
git checkout agent/public-landing
```

### Terminal 1 — Django backend

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate
python manage.py check
python manage.py runserver
```

Backend health endpoint:

```text
http://127.0.0.1:8000/api/health/
```

Expected response:

```json
{
  "status": "ok",
  "service": "domaintwin-api"
}
```

### Terminal 2 — Next.js frontend

```powershell
cd frontend
Copy-Item .env.example .env.local
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

The footer should display `API ONLINE` while Django is running.

### Production-build check

```powershell
cd frontend
npm run build
```

### Django check

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python manage.py check
```

## Public/private boundary

Public routes implemented now:

- `/` — public DomainTwin landing
- `/login` — placeholder

Planned authenticated routes:

- `/app/overview`
- `/app/domains`
- `/app/incidents`
- `/app/snapshots`
- `/app/recovery`
- `/app/emergency-domains`
- `/app/reports`
- `/app/settings`

## Design language

The public site follows the approved Google Stitch product language used by the private application:

- deep navy `#0F172A`
- primary blue `#003EC7` / `#0052FF`
- canvas `#F8F9FA`
- border `#E2E8F0`
- success `#10B981`
- warning `#F59E0B`
- critical `#EF4444`
- Inter + JetBrains Mono

The visual system intentionally avoids gradients, glassmorphism and decorative AI imagery.
