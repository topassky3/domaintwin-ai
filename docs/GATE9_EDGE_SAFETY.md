# Gate 9 — Edge Cases + Safety

## Goal

Prove that DomainTwin fails safely under provider, race-condition and AI failure scenarios without ever reporting false recovery success or weakening the sandbox/production boundary.

Gate 9 is intentionally a **hardening + regression gate**, not a feature-expansion gate.

## Acceptance matrix

| Edge case | Expected behavior | Proof |
|---|---|---|
| Invalid name.com token / HTTP 401 | Preserve explicit 401, mark non-retryable, do not leak credentials | `test_invalid_token_401_is_explicit_and_not_retryable` |
| HTTP 429 | Normalize provider error and mark retryable | `test_rate_limit_429_is_marked_retryable` |
| Provider 5xx | Normalize provider error and mark retryable | `test_provider_5xx_is_marked_retryable` |
| Network failure | Normalize to retryable 503 | `test_network_failure_is_normalized_to_retryable_503` |
| Timeout | Normalize to retryable 504 | `test_timeout_is_normalized_to_retryable_504` |
| Record already deleted before apply | If live DNS already equals target, skip mutation and verify recovery | `test_record_already_deleted_before_apply_becomes_verified_noop` |
| Record unexpectedly added after preview | Mark recovery plan `STALE`, mutate nothing, require regenerated preview | `test_unexpected_record_added_after_preview_marks_plan_stale_without_mutation` |
| Partial rollback | Persist `PARTIAL`, preserve successful/failed operation evidence, never emit completed success | `test_second_operation_failure_is_partial_never_false_success` |
| AI provider unavailable | Return deterministic fallback with `UNAVAILABLE`; AI cannot mutate DNS; human approval remains required | `test_ai_unavailable_returns_safe_fallback_and_preserves_human_boundary` |
| Sandbox vs production | Distinct API base URL and visible UI environment; production mutation requires explicit second opt-in | `test_production_has_distinct_base_url_and_mutation_requires_second_opt_in` + Gate 9 contract |
| Secrets absent from browser source | No provider token/API key/Authorization material in `frontend/src` | Gate 9 contract |

## Important behavior decisions

### Already-deleted record

If a planned DELETE is no longer needed because another actor removed the record and the **entire live DNS state now matches the known-good fingerprint**, DomainTwin does not treat the provider race as a failure. It follows the existing verification-only path:

```text
approved preview
→ fresh provider read
→ live fingerprint already equals target
→ zero mutation
→ verification succeeds
→ RECOVERED
```

This is safer than attempting a stale DELETE by provider record ID.

### Unexpected record after preview

If any live DNS change occurs after preview and the resulting state is not already the known-good target, the plan is stale:

```text
preview fingerprint A
→ operator approves
→ external actor changes DNS to fingerprint B
→ apply preflight sees B != A
→ PLAN_STALE
→ zero mutation
→ regenerate preview
```

DomainTwin never applies an old mutation plan to a changed live state.

### Partial rollback

Provider mutation failure after one or more successful operations produces `PARTIAL`, not `RECOVERED`. Each operation result preserves provider status and retryability, and `RECOVERY_COMPLETED` is absent until post-change verification succeeds.

### AI unavailable

AI remains optional. With `AI_PROVIDER=disabled` or a provider outage, DomainTwin stores an `UNAVAILABLE` explanation with deterministic fallback guidance. DNS diff, risk, recovery planning and approval remain independent from AI.

## Static Gate 9 contract

From `frontend/`:

```powershell
npm run gate9:contract
```

The contract verifies:

- 429/5xx/network/timeout failure classification;
- explicit HTTP status preservation for auth failures;
- stale-plan protection;
- verified no-op recovery when live DNS already equals target;
- PARTIAL/FAILED semantics;
- AI `UNAVAILABLE` fallback + no-mutation boundary;
- SANDBOX/PRODUCTION visual distinction;
- production mutation and registration guards;
- absence of provider credential/auth material from `frontend/src`;
- all ten dedicated Gate 9 regression names are present.

## Local verification

Keep all provider mutations disabled. Gate 9 does not require intentionally attacking the live sandbox account with bad credentials or rate-limit traffic; the provider failures are deterministically simulated at the HTTP boundary.

```powershell
cd C:\Users\felipe\Desktop\domaintwin-ai\backend
.\.venv\Scripts\Activate.ps1

$env:NAMECOM_ENVIRONMENT="sandbox"
$env:NAMECOM_ALLOW_MUTATIONS="0"
$env:NAMECOM_ALLOW_PRODUCTION_MUTATIONS="0"
$env:NAMECOM_ALLOW_DOMAIN_REGISTRATION="0"
$env:AI_PROVIDER="disabled"

python manage.py check
python manage.py test core.test_safety
python manage.py test core

cd ..\frontend
npm run gate7:contract
npm run gate8:contract
npm run gate9:contract
npm run typecheck
npm run build
```

## Gate 9 PASS definition

Gate 9 passes only when:

1. dedicated safety tests pass;
2. full core regression still passes;
3. Gate 7 and Gate 8 contracts still pass;
4. Gate 9 contract passes;
5. TypeScript and production build pass;
6. runtime flags remain safe (`MUT=0`, `PROD_MUT=0`, `REG=0`);
7. generated build artifacts are cleaned;
8. working tree is clean and local HEAD equals remote branch HEAD.
