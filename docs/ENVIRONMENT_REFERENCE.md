# DomainTwin AI — Environment Variable Reference

All provider credentials are server-side. Do not prefix name.com or AI secret variables with `NEXT_PUBLIC_`.

## Backend — `backend/.env`

| Variable | Purpose | Safe/default demo value |
|---|---|---|
| `DJANGO_SECRET_KEY` | Django cryptographic secret | unique local value |
| `DJANGO_DEBUG` | Django debug mode | `1` locally |
| `DJANGO_ALLOWED_HOSTS` | allowed host names | `127.0.0.1,localhost` |
| `NAMECOM_ENVIRONMENT` | provider environment | `sandbox` |
| `NAMECOM_USERNAME` | name.com account username | secret/configured locally |
| `NAMECOM_API_TOKEN` | name.com API token | secret/configured locally |
| `NAMECOM_TIMEOUT_SECONDS` | provider request timeout | `10` |
| `NAMECOM_ALLOW_MUTATIONS` | enables DNS writes | `0` |
| `NAMECOM_ALLOW_PRODUCTION_MUTATIONS` | second guard for production writes | `0` |
| `NAMECOM_ALLOW_DOMAIN_REGISTRATION` | additional Gate 8 registration guard | `0` |
| `DOMAIN_HEALTH_TIMEOUT_SECONDS` | HTTP/HTTPS health timeout | `4` |
| `AI_PROVIDER` | optional explanation provider | `disabled` |
| `AI_MODEL` | configured AI model | project-configured value |
| `OPENAI_API_KEY` | AI provider key | empty unless explicitly used |
| `AI_API_BASE_URL` | OpenAI-compatible endpoint | `https://api.openai.com/v1` |
| `AI_TIMEOUT_SECONDS` | AI request timeout | `15` |
| `AI_MAX_OUTPUT_TOKENS` | explanation output limit | `700` |

## Frontend — `frontend/.env.local`

| Variable | Purpose | Local value |
|---|---|---|
| `API_BASE_URL` | server-side Next proxy target | `http://127.0.0.1:8000` |
| `NEXT_PUBLIC_API_BASE_URL` | public health-status component base URL | `http://127.0.0.1:8000` |

`NEXT_PUBLIC_API_BASE_URL` is not a credential. It is only a local/public service location.

## Safe baseline

Before tests, rehearsal, screenshot capture or video recording, start from:

```text
NAMECOM_ENVIRONMENT=sandbox
NAMECOM_ALLOW_MUTATIONS=0
NAMECOM_ALLOW_PRODUCTION_MUTATIONS=0
NAMECOM_ALLOW_DOMAIN_REGISTRATION=0
AI_PROVIDER=disabled
```

## Mutation matrix

| Environment | `ALLOW_MUTATIONS` | `ALLOW_PRODUCTION_MUTATIONS` | Result |
|---|---:|---:|---|
| sandbox | 0 | 0 | writes blocked |
| sandbox | 1 | 0 | controlled DNS writes allowed |
| production | 1 | 0 | production writes still blocked |
| production | 1 | 1 | production DNS writes technically allowed — **not for hackathon rehearsal** |

Domain registration additionally requires:

```text
NAMECOM_ALLOW_DOMAIN_REGISTRATION=1
```

and the application hard-blocks registration unless `NAMECOM_ENVIRONMENT=sandbox`.

## AI boundary

`AI_PROVIDER=disabled` is a fully supported state. Monitoring, deterministic risk, recovery planning, provider mutation and verification do not depend on AI availability.

If AI is enabled, keep the key server-side and never display raw prompts containing secrets.

## What must never be committed

- real `DJANGO_SECRET_KEY`
- real `NAMECOM_API_TOKEN`
- real `OPENAI_API_KEY`
- Basic Authorization header values
- `.env`
- `.env.local`
- screenshots containing credentials or personal contact data
