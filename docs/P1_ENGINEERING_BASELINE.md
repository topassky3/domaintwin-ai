# P1 — Engineering Baseline

P1 turns the frozen hackathon build into a safer engineering baseline without changing the DomainTwin recovery model.

## Scope

P1-A adds automatic CI for every pull request to `main` and every push to `main`.

The CI proves two independent surfaces.

### Backend

- Python 3.12
- dependency installation from `backend/requirements.txt`
- Python dependency-graph validation with `pip check`
- exact verification of the pinned direct backend versions
- `makemigrations --check --dry-run`
- Django `check`
- complete `core` regression suite
- no real name.com or AI credentials
- sandbox environment
- all provider mutation flags OFF
- AI disabled

### Frontend

- Node.js 20 application runtime
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

P1-B pins every direct frontend dependency in `package.json` to the exact version already resolved by the proven lockfile. It does not upgrade packages. The verified versions are:

```text
next              16.3.1
react             19.2.8
react-dom         19.2.8
@types/node       26.2.0
@types/react      19.2.18
@types/react-dom  19.2.4
typescript        7.0.2
```

The P1 contract rejects `latest` and other non-exact direct frontend dependency specifications and verifies that every pinned direct dependency resolves to the same version in `package-lock.json`.

P1-C pins the direct Python runtime dependencies to the exact versions already proven by GitHub Actions:

```text
Django==5.2.17
python-dotenv==1.2.3
```

The CI additionally runs `python -m pip check` and verifies the installed package metadata before Django checks/tests. This checkpoint intentionally pins the direct runtime contract without introducing a new Python packaging tool or changing application behavior.

## GitHub Actions runtime hardening

P1-D removes the Node-runtime deprecation warnings emitted by the older official GitHub Actions. The action releases were checked before the update and their release commits are pinned directly in the workflow:

```text
actions/checkout v7.0.1
  3d3c42e5aac5ba805825da76410c181273ba90b1

actions/setup-python v7.0.0
  5fda3b95a4ea91299a34e894583c3862153e4b97

actions/setup-node v7.0.0
  820762786026740c76f36085b0efc47a31fe5020
```

Those releases use Node 24 internally. The explicit `node-version: "20"` in the frontend job is a separate concern: it remains the application/runtime version used to build DomainTwin and is not the deprecated internal runtime of the GitHub Actions themselves.

Pinning the action commits also prevents an action tag from silently changing the code executed by CI.

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

## P1-C acceptance criteria

P1-C passes only when all of the following are true:

1. `backend/requirements.txt` uses exact direct dependency pins.
2. Django is pinned to `5.2.17`, the version already proven by CI.
3. python-dotenv is pinned to `1.2.3`, the version already proven by CI.
4. `python -m pip check` reports no broken dependency relationships.
5. CI verifies the installed Django and python-dotenv versions before running application checks.
6. `makemigrations --check --dry-run` remains clean.
7. Django `check` remains clean.
8. all 90 `core` tests still pass.
9. frontend contracts/typecheck/build remain green in CI.
10. no DomainTwin recovery, incident, risk, emergency or AI decision logic is modified.

## P1-D acceptance criteria

P1-D passes only when all of the following are true:

1. checkout is pinned to the verified `v7.0.1` commit.
2. setup-python is pinned to the verified `v7.0.0` commit.
3. setup-node is pinned to the verified `v7.0.0` commit.
4. the P1 contract rejects the old checkout/setup action references.
5. GitHub Actions completes backend and frontend jobs successfully.
6. the prior Node 20 action-runtime deprecation warning is absent from the new run logs.
7. application Node.js remains explicitly controlled for the DomainTwin frontend build.
8. the local P1 contract passes after syncing the branch.
9. the local tree is clean and local HEAD equals the remote branch HEAD.
10. no DomainTwin product logic is changed.

## Local verification — Windows PowerShell

From the repository root:

```powershell
cd C:\Users\felipe\Desktop\domaintwin-ai

git fetch origin
git switch agent/p1-engineering-baseline
git pull --ff-only origin agent/p1-engineering-baseline
```

Backend P1-C:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip check
python -c "import importlib.metadata as m; print('Django=', m.version('Django')); print('python-dotenv=', m.version('python-dotenv'))"
python manage.py makemigrations --check --dry-run
python manage.py check
python manage.py test core
```

Frontend/P1 contract:

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

P1-D can be locally checked without another full application regression after CI is green:

```powershell
cd frontend
npm run p1:contract
cd ..
git diff --check
git status --short
git rev-parse HEAD
git rev-parse origin/agent/p1-engineering-baseline
```

Cleanup after a frontend build, if needed:

```powershell
git restore frontend/next-env.d.ts
```

## Remaining P1 work

P1-E applies repository protection policy to `main` using the successful CI checks as the merge gate. That step includes explicit GitHub web-page instructions because repository rules are account/repository settings rather than application code.

## Out of scope for P1

- authentication
- RBAC
- multi-tenancy
- PostgreSQL migration
- monitoring scheduler
- alerts
- production deployment
- billing
- recovery-engine refactors

Those remain later productization phases. P1 changes the engineering safety net and reproducibility, not the product behavior.
