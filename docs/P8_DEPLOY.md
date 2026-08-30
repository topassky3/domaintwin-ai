# P8 — Deploy

P8 packages the completed DomainTwin hackathon control plane into one reproducible single-host deployment. It intentionally does **not** turn the project into an HA production platform.

## Deployment shape

```text
Internet
   |
   | 80/443
   v
 Caddy
   |
   v
Next.js :3000  ----server-side---->  Django/Gunicorn :8000
                                          |
                                          +---- shared SQLite volume
                                          |
                                      Monitoring Lite worker
```

Only Caddy publishes host ports. The browser never receives Name.com credentials and neither Django nor Next.js is directly published by Compose.

## Files

- `compose.yaml` — one-command single-host stack.
- `deploy/Caddyfile` — TLS termination and reverse proxy.
- `deploy/.env.example` — deployment environment template; safe placeholders only.
- `backend/Dockerfile` — Python 3.12 + Gunicorn runtime.
- `backend/docker-entrypoint.sh` — web migration ownership and monitor startup ordering.
- `frontend/Dockerfile` — Next.js standalone runtime.
- `frontend/scripts/p8-contract.mjs` — deployment invariant contract.

## Before deploying

1. Install Docker Engine with the Compose plugin on the VPS.
2. Point the intended public hostname A/AAAA record at the VPS.
3. Allow inbound TCP 80/443. QUIC/HTTP3 can additionally use UDP 443.
4. Keep Name.com in `sandbox` for the hackathon.
5. Never commit `deploy/.env`.

Create runtime configuration:

```bash
cp deploy/.env.example deploy/.env
```

Edit at minimum:

- `DOMAIN_TWIN_HOST`
- `DJANGO_SECRET_KEY`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `NAMECOM_USERNAME`
- `NAMECOM_API_TOKEN`

The template deliberately keeps `NAMECOM_ALLOW_PRODUCTION_MUTATIONS=0`. Sandbox recovery is armed with `NAMECOM_ALLOW_MUTATIONS=1`; emergency sandbox registration remains optional.

## Build and start

```bash
docker compose --env-file deploy/.env up -d --build
```

Inspect service state:

```bash
docker compose --env-file deploy/.env ps
docker compose --env-file deploy/.env logs --tail 100 backend frontend monitor caddy
```

The backend container owns `migrate`. The monitor container waits until migrations are complete before starting `monitor_domaintwin --loop`.

## First installation bootstrap

For a fresh deployment, create the demo user first:

```bash
docker compose --env-file deploy/.env exec backend python manage.py createsuperuser
```

Give that existing user the P2 bootstrap role, then create the tenant membership:

```bash
docker compose --env-file deploy/.env exec backend python manage.py set_domaintwin_role <username> ADMIN
docker compose --env-file deploy/.env exec backend python manage.py bootstrap_domaintwin_org hackathon "DomainTwin Hackathon" --username <username>
```

Attach the Name.com sandbox domain used by the demo:

```bash
docker compose --env-file deploy/.env exec backend python manage.py attach_domaintwin_domains hackathon --domain <sandbox-domain>
```

Then use the private workspace to create/mark the exact known-good baseline required by the recovery flow.

## Judge-day preflight

Run P7 readiness inside the deployed backend:

```bash
docker compose --env-file deploy/.env exec backend python manage.py demo_readiness --organization hackathon
```

A demo intended to exercise live sandbox recovery should end with `STATUS=READY`. Monitoring freshness and emergency registration can remain warnings depending on the selected scenario.

Also verify the public safe demo before presenting:

```bash
curl -I https://<DOMAIN_TWIN_HOST>/demo
```

## Operational commands

Restart without rebuilding:

```bash
docker compose --env-file deploy/.env restart
```

Rebuild after pulling a new commit:

```bash
docker compose --env-file deploy/.env up -d --build
```

Follow monitor output:

```bash
docker compose --env-file deploy/.env logs -f monitor
```

Stop the stack while preserving data/TLS volumes:

```bash
docker compose --env-file deploy/.env down
```

Do **not** add `-v` unless intentionally deleting the DomainTwin SQLite and Caddy volumes.

## SQLite backup before judge day

Pause writers, copy the database, then restart:

```bash
docker compose --env-file deploy/.env stop monitor backend
docker cp "$(docker compose --env-file deploy/.env ps -q backend):/data/db.sqlite3" ./domaintwin-backup.sqlite3
docker compose --env-file deploy/.env start backend monitor
```

## P8 acceptance criteria

P8 is closed when:

1. Compose defines exactly the small hackathon runtime: `caddy`, `frontend`, `backend`, `monitor`.
2. Only Caddy publishes host ports.
3. Name.com secrets are injected only into backend/monitor.
4. Django persists SQLite at `/data/db.sqlite3` with an explicit busy timeout.
5. Backend migrations have one owner and the monitor waits for them.
6. Next.js builds in standalone mode.
7. Caddy terminates public TLS and proxies to Next.js.
8. `docker compose config` succeeds from the deployment template.
9. CI actually builds backend and frontend container images.
10. P1–P8 contracts, backend regression, TypeScript and production build remain green.
11. P7 `demo_readiness` remains the final live-environment gate after deployment.

## Explicitly deferred after the hackathon

- PostgreSQL/managed database migration.
- multiple replicas and distributed locking.
- external secret manager/KMS.
- managed queues or Redis/Celery.
- Kubernetes/orchestration.
- zero-downtime multi-node rollout.
- centralized logs/metrics/alert delivery.

Those are production evolution items, not blockers for the hackathon deployment.
