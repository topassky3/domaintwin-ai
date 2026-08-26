# P1 — Engineering Baseline

P1 turns the frozen hackathon build into a safer engineering baseline without changing the DomainTwin recovery model.

## Scope

P1-A adds automatic CI for every pull request to `main` and every push to `main`.

The CI must prove two independent surfaces:

### Backend

- Python 3.12
- dependency installation from `backend/requirements.txt`
- `makemigrations --check --dry-run`
- Django `check`
- complete `core` regression suite
- no real name.com or AI credentials
- sandbox environment
- all provider mutation flags OFF
- AI disabled

### Frontend

- Node.js 20
- exact install from the committed lockfile using `npm ci`
- Gate 7/8/9/10/11 contracts
- P1 CI contract
- TypeScript
- production build

## Security invariant

CI must never need production secrets.

The workflow uses intentionally fake name.com credentials because unit/regression tests must isolate provider behavior. Runtime mutation flags remain:

```text
NAMECOM_ENVIRONMENT=sandbox
NAMECOM_ALLOW_MUTATIONS=0
NAMECOM_ALLOW_PRODUCTION_MUTATIONS=0
NAMECOM_ALLOW_DOMAIN_REGISTRATION=0
AI_PROVIDER=disabled
```

If a future test unexpectedly requires a real provider credential, that is a design regression and must be reviewed before adding any GitHub secret.

## Reproducibility rule

Frontend CI uses:

```text
npm ci
```

not `npm install`.

The committed `package-lock.json` is the dependency-tree authority for CI.

Python dependencies remain bounded by `requirements.txt` during P1-A. Exact Python locking is evaluated separately in P1-B so CI establishment and dependency-policy changes are not mixed in one checkpoint.

## Generated artifacts

`*.tsbuildinfo` is a local TypeScript cache artifact and must not appear as an untracked repository change after type checking.

`next-env.d.ts` remains tracked because it is part of the Next.js project contract; local generated drift should be restored rather than ignored.

## P1-A acceptance criteria

P1-A passes only when all of the following are true:

1. `.github/workflows/ci.yml` exists.
2. CI runs for pull requests to `main`, pushes to `main`, and manual dispatch.
3. Backend CI uses safe fake credentials and all mutation flags remain OFF.
4. Backend migration drift, Django check and all 90 baseline tests pass.
5. Frontend dependencies are installed with `npm ci`.
6. Gate 7/8/9/10/11 and P1 contracts pass.
7. TypeScript passes.
8. Next.js production build passes.
9. `*.tsbuildinfo` is ignored.
10. local working tree is clean after generated artifact cleanup.
11. GitHub Actions reports both backend and frontend jobs successful on the P1 pull request.

## Local verification — Windows PowerShell

From the repository root:

```powershell
cd C:\Users\felipe\Desktop\domaintwin-ai

git fetch origin
git switch agent/p1-engineering-baseline
git pull --ff-only origin agent/p1-engineering-baseline
```

Backend:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python manage.py makemigrations --check --dry-run
python manage.py check
python manage.py test core
```

Frontend:

```powershell
cd ..\frontend
npm ci
npm run gate7:contract
npm run gate8:contract
npm run gate9:contract
npm run gate10:contract
npm run gate11:contract
npm run p1:contract
npm run typecheck
npm run build
```

Cleanup and repository proof:

```powershell
git restore next-env.d.ts
cd ..
git diff --check
git status --short
git rev-parse HEAD
git rev-parse origin/agent/p1-engineering-baseline
```

## Out of scope for P1-A

- authentication
- RBAC
- multi-tenancy
- PostgreSQL migration
- monitoring scheduler
- alerts
- production deployment
- billing
- recovery-engine refactors

Those remain later productization phases. P1-A changes the engineering safety net, not the product behavior.
