# Gate 7 — Private Product UI

Gate 7 turns the verified DomainTwin backend into the live product workspace used by the hackathon demo.

## Required routes

```text
/app/overview
/app/domains
/app/domains/:domain
/app/domains/:domain/dns
/app/domains/:domain/snapshots
/app/incidents
/app/incidents/:id
/app/recovery
```

`/app` redirects to `/app/overview`.

## Architecture

The browser does **not** call Django provider endpoints directly. Client components call:

```text
/api/domaintwin/*
```

A Next.js route handler proxies those requests server-side to:

```text
API_BASE_URL=http://127.0.0.1:8000
```

This gives the UI one same-origin API boundary and keeps name.com/OpenAI credentials out of browser code and payloads.

## Product flow

```text
Overview
  -> Domain workspace
  -> Live DNS + deterministic diff
  -> Incident evidence
  -> Evidence-based AI explanation
  -> Recovery preview
  -> Human approval
  -> Apply through name.com
  -> Expected vs actual verification
  -> RECOVERED / PARTIAL / FAILED / STALE
```

The public `/demo` remains safe and simulated. `/app/*` is the live configured workspace.

## Safety invariants

- Permanent SANDBOX / PRODUCTION badge comes from the backend name.com status endpoint.
- Provider secrets are never exposed to React client code.
- AI secrets are never exposed to React client code.
- Recovery Preview does not mutate DNS.
- Approve sends explicit `{ "approve": true }`.
- Apply appears only when the backend returns `canApply=true`.
- Backend Gate 5 mutation guards remain authoritative.
- RECOVERED is rendered from persisted recovery state after verification, never inferred by the frontend.
- AI probable cause is visually separated from deterministic factors/evidence.
- Loading, error and empty states exist for external provider calls.

## Frontend verification

From repository root:

```powershell
cd C:\Users\felipe\Desktop\domaintwin-ai\frontend
npm ci
npm run gate7:contract
npm run typecheck
npm run build
```

Expected:

```text
GATE 7 CONTRACT PASS
Required routes: 8/8
```

`typecheck` and `build` must exit with code 0.

## Backend regression

```powershell
cd C:\Users\felipe\Desktop\domaintwin-ai\backend
.\.venv\Scripts\Activate.ps1
python manage.py makemigrations --check
python manage.py migrate
python manage.py check
python manage.py test core
```

Expected core suite remains:

```text
Found 69 test(s).
.....................................................................
OK
```

## Safe UI smoke test

Keep:

```env
AI_PROVIDER=disabled
NAMECOM_ENVIRONMENT=sandbox
NAMECOM_ALLOW_MUTATIONS=0
NAMECOM_ALLOW_PRODUCTION_MUTATIONS=0
```

Backend terminal:

```powershell
cd C:\Users\felipe\Desktop\domaintwin-ai\backend
.\.venv\Scripts\Activate.ps1
python manage.py runserver
```

Frontend terminal:

```powershell
cd C:\Users\felipe\Desktop\domaintwin-ai\frontend
npm run dev
```

Open:

```text
http://localhost:3000/app/overview
```

Verify:

1. permanent SANDBOX badge and name.com connected state;
2. overview shows the real sandbox domain;
3. Domains -> domain workspace has no dead end;
4. DNS reads real records and known-good diff;
5. Snapshots list the existing known-good snapshot;
6. Incidents list the Gate 4/5 incident history;
7. incident detail displays deterministic factors and timeline;
8. AI panel degrades explicitly while `AI_PROVIDER=disabled`;
9. recovery workspace can read existing plans and create a preview without mutation;
10. browser Network requests use `/api/domaintwin/*`, not provider credentials.

## Controlled Golden UI smoke test

Only after the safe smoke passes.

Use the same sandbox-only safety process used by Gate 5. Production mutations stay disabled at all times:

```env
NAMECOM_ENVIRONMENT=sandbox
NAMECOM_ALLOW_MUTATIONS=1
NAMECOM_ALLOW_PRODUCTION_MUTATIONS=0
AI_PROVIDER=openai
```

Create one controlled dangerous sandbox DNS change using the already-verified Gate 1 mutation endpoint or existing drill procedure. Then perform the visible browser flow:

```text
Domain -> Evaluate now
-> INCIDENT / CRITICAL
-> Incident -> Generate explanation
-> Recovery -> Create rollback preview
-> Approve recovery
-> Apply approved recovery
-> verification MATCH
-> RECOVERED
```

Acceptance evidence should include screenshots of:

- CRITICAL domain/incident state;
- evidence-based AI explanation;
- exact rollback preview;
- explicit approval boundary;
- RECOVERED + expected/actual fingerprint match;
- audit trail.

Immediately after the controlled drill return to:

```env
AI_PROVIDER=disabled
NAMECOM_ALLOW_MUTATIONS=0
NAMECOM_ALLOW_PRODUCTION_MUTATIONS=0
```

Then rerun backend tests and frontend build.

## Gate 7 acceptance

Gate passes only when:

- all 8 required routes exist and navigate without dead ends;
- `npm run gate7:contract` passes;
- TypeScript passes;
- production build passes;
- 69/69 backend tests still pass;
- permanent environment indicator is visible;
- real name.com domain/DNS state is visible;
- deterministic Healthy / Incident / Recovered states are visually distinct;
- incident evidence and AI explanation are visually separated;
- recovery preview / approve / apply / verify works through the UI;
- loading/error/empty states are demonstrable;
- provider/API depth is obvious;
- no provider or AI secret is exposed in browser payloads or committed files;
- final mutation flags return to zero;
- working tree is clean.
