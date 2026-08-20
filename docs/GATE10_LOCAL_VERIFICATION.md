# Gate 10 — Local Verification

Gate 10 changes presentation/documentation and adds no provider mutation path. Keep the runtime in the normal safe configuration during verification.

## Expected branch

```text
agent/gate10-startup-feasibility
```

## Safe backend flags

```text
NAMECOM_ENVIRONMENT=sandbox
NAMECOM_ALLOW_MUTATIONS=0
NAMECOM_ALLOW_PRODUCTION_MUTATIONS=0
NAMECOM_ALLOW_DOMAIN_REGISTRATION=0
AI_PROVIDER=disabled
```

## Focused Gate 10 proof

From `frontend/`:

```powershell
npm run gate10:contract
npm run typecheck
npm run build
```

The production build must include:

```text
/feasibility
```

## Browser proof

Run Django and Next.js in the safe configuration and open:

```text
http://localhost:3000/feasibility
```

A judge should be able to identify within roughly 30 seconds:

1. who pays;
2. what problematic/expensive event DomainTwin addresses;
3. why verified recovery is better than manual reconstruction;
4. why name.com is central;
5. what becomes a SaaS after the hackathon.

The page must visibly label the business model as a **hypothesis**, not validated traction/pricing.

## Final regression before merge

Backend:

```powershell
python manage.py makemigrations --check --dry-run
python manage.py check
python manage.py test core
```

Frontend:

```powershell
npm run gate7:contract
npm run gate8:contract
npm run gate9:contract
npm run gate10:contract
npm run typecheck
npm run build
```

Then remove only generated build artifacts, run `git diff --check`, require a clean working tree, and confirm local HEAD equals the remote Gate 10 branch HEAD before merge.
