# DomainTwin AI — application boundary

## Public

- `/` — explains the problem and recovery story in less than 15 seconds
- `/login` — entry point to the future authenticated workspace

## Private (planned)

- `/app/overview`
- `/app/domains`
- `/app/incidents`
- `/app/snapshots`
- `/app/recovery`
- `/app/emergency-domains`
- `/app/reports`
- `/app/settings`

## Core demo story

Healthy DNS → dangerous change → drift detected → incident explained → human-approved rollback → DNS verified → service recovered.

The LLM is explanatory only. DNS mutations are planned deterministically and require human approval.
