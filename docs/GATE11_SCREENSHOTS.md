# Gate 11 — Real Screenshot Checklist

Devpost should show the working product, not decorative mockups.

Capture screenshots only after the corresponding live/sandbox state is verified.

## Required captures

### 1. Product overview — Healthy

Route: `/app/overview`

Must show:

- DomainTwin product shell
- SANDBOX indicator
- name.com connected
- selected real sandbox domain
- healthy/low-risk state

Suggested filename:

```text
01-overview-healthy.png
```

### 2. CRITICAL incident + evidence

Route: `/app/incidents/<id>`

Must show:

- CRITICAL severity / risk
- changed DNS evidence
- deterministic factors
- incident timeline or evidence section

Suggested filename:

```text
02-critical-incident.png
```

### 3. AI explanation

Same incident route.

Must show:

- evidence-based explanation
- probable cause vs fact distinction if visible
- confidence/evidence references
- no secret/provider credentials

Suggested filename:

```text
03-ai-evidence.png
```

### 4. Recovery preview

Route: recovery UI / incident recovery section.

Must show:

- known-good snapshot
- exact CREATE / UPDATE / DELETE operation(s)
- human approval boundary

Suggested filename:

```text
04-recovery-preview.png
```

### 5. Verified RECOVERED

Must show:

- `RECOVERED`
- expected fingerprint
- actual fingerprint
- `MATCH YES`
- provider/audit evidence if readable

Suggested filename:

```text
05-recovered-match.png
```

### 6. Emergency search + exact availability

Route: `/app/emergency`

Must show:

- real name.com search results
- exact selected candidate
- CHECK AVAILABLE
- sandbox / registration boundary

Suggested filename:

```text
06-emergency-search-check.png
```

### 7. Emergency READY

Must show:

- exact registered sandbox domain
- clone operation(s)
- expected fingerprint
- actual fingerprint
- `MATCH YES`
- `READY`

Suggested filename:

```text
07-emergency-ready.png
```

### 8. Startup feasibility

Route: `/feasibility`

Must show at least the five 30-second judge questions or the paid-problem/business-model section.

Suggested filename:

```text
08-feasibility.png
```

## Capture rules

- Use the same browser width/theme across images.
- Avoid browser tabs with personal names, email or unrelated projects.
- Do not expose developer tools with Authorization headers.
- Do not capture `.env` or terminals containing tokens.
- Crop only empty browser chrome; do not crop evidence necessary to understand the state.
- Prefer 16:9 or wide desktop composition for Devpost readability.
- Keep text readable at normal viewing size.
- Do not label a mock state as real.

## Selection rule

Devpost does not need all eight if the page becomes visually heavy. Minimum strong set:

1. CRITICAL incident,
2. recovery preview,
3. RECOVERED / MATCH YES,
4. emergency SEARCH/CHECK,
5. emergency READY / MATCH YES.

Add overview and feasibility only if they improve the story rather than repeating it.

## Gate closure

This checklist is prepared, but Gate 11 does **not** mark screenshots complete until real image files have actually been captured and reviewed.
