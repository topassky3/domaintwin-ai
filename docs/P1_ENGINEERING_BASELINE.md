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

P1-B also pins every direct frontend dependency in `package.json` to the exact version already resolved by the proven lockfile. It does not upgrade packages. The verified versions are:

```text
next              16.3.1
react             19.2.8
react-dom         19.2.8
@types/node       26.2.0
@types/react      19.2.18
@types/react-dom  19.2.4
typescript        7.0.2
```

The P1 contract rejects `latest` and other non-exact direct dependency specifications and verifies that every pinned direct dependency resolves to the same version in `package-lock.json`.

Python dependencies remain bounded by `requirements.txt` during P1-A/P1-B. Exact Python locking is a separate checkpoint so frontend pinning and Python packaging policy are not mixed into one change.

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

## P1-B acceptance criteria

P1-B passes only when all of the following are true:

1. `frontend/package.json` contains no `latest` direct dependency specifications.
2. Every direct frontend dependency is pinned to an exact version.
3. Each pinned version exactly matches the version already resolved in `package-lock.json`.
4. `npm ci` succeeds without changing the dependency tree.
5. Gate 7/8/9/10/11 and P1 contracts still pass.
6. TypeScript still passes.
7. Next.js production build still passes.
8. GitHub Actions backend and frontend jobs remain successful.
9. No DomainTwin recovery, incident, risk, emergency or AI decision logic is modified.
10. local working tree is clean after generated artifact cleanup.

## Local verification — Windows PowerShell

From the repository root:

```powershell
cd C:\Users\felipe\Desktop\domaintwin-ai

git fetch origin
git switch agent/p1-engineering-baseline
git pull --ff-only origin agent/p1-engineering-baseline
```

Backend regression, when requested:

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

## Out of scope for P1-A / P1-B

- authentication
- RBAC
- multi-tenancy
- PostgreSQL migration
- monitoring scheduler
- alerts
- production deployment
- billing
- recovery-engine refactors
- Python dependency lock policy

Those remain later productization checkpoints. P1 changes the engineering safety net and reproducibility, not the product behavior.
