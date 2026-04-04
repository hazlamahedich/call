# TEA Automation Summary — Stories 1-1, 1-2, 1-3

**Date**: 2026-03-28  
**Workflow**: tea-automate  
**Stories**: 1-1, 1-2, 1-3  
**Team**: team mantis a

---

## P1 Fixes Applied

### Fix 1: test_009 — Hardcoded DB URL fallback
- **File**: `apps/api/tests/fixtures/test_rls.py` (lines 247-252)
- **Before**: Hardcoded fallback `postgresql+asyncpg://test_rls_user@localhost:5432/call_test`
- **After**: `pytest.skip("TEST_RLS_DATABASE_URL not set — skipping non-superuser RLS verification")`
- **Result**: test_009 now correctly SKIPPED when env var not set

### Fix 2: test_008 — Conditional guard
- **File**: `apps/api/tests/fixtures/test_rls.py` (lines 212-218)
- **Before**: `created.id if created.id else 0` — masked failures by passing 0 as fallback
- **After**: `assert created.id is not None` before using the id
- **Result**: test_008 now fails fast if create didn't return an id

### Fix 3: CI timeout multiplier
- **File**: `apps/api/tests/test_rls_performance.py` (lines 95, 120)
- **Before**: Fixed thresholds `1000ms`, `500ms`
- **After**: `CI_MULTIPLIER = float(os.environ.get("CI_TIMEOUT_MULTIPLIER", "1.0"))` multiplied thresholds
- **Result**: Performance tests now scale properly on slower CI runners

---

## New Tests Created

### test_constants.py (rewritten from garbage content)
- Cross-source AUTH_ERROR_CODES synchronization (TS ↔ middleware/auth ↔ dependencies/org_context)
- Cross-source TENANT_ERROR_CODES verification
- **4 tests**

### test_error_codes_sync.py (new file)
- Backend AUTH_ERROR_CODES consistency between middleware and dependencies
- Expected auth error key presence
- Auth error value format validation (uppercase, matches key)
- TENANT_ERROR_CODES format validation for all 3 codes
- **6 tests**

### test_tenant_service.py (new file)
- TenantService.update() with None id — raises TenantContextError
- TenantService.create() with no tenant context — raises TenantContextError
- _row_to_instance() with full row
- _row_to_instance() with truncated row
- **4 tests**

### test_webhooks.py (membership handlers added)
- membership.updated webhook handler
- membership.deleted webhook handler
- **2 new tests**

### test_auth.py (auth skip paths added)
- Skip auth for /health, /docs, /openapi.json (integration)
- Direct unit tests for _should_skip_auth()
- SKIP_AUTH_PATHS constant completeness check
- **6 new tests**

### support/factories.py (new data factory)
- LeadFactory with build(), build_batch(), reset() methods
- Auto-incrementing unique names/emails

---

## Test Results

| Metric | Count |
|--------|-------|
| Passed | 78 |
| Skipped | 16 (contract tests — expected) |
| Failed | 0 |
| **Total** | **94** |

---

## Files Modified/Created

| File | Action | Description |
|------|--------|-------------|
| `apps/api/tests/fixtures/test_rls.py` | Modified | P1 fixes for test_008, test_009 |
| `apps/api/tests/test_rls_performance.py` | Modified | CI multiplier for timing thresholds |
| `apps/api/tests/test_constants.py` | Rewritten | Error code sync tests (was garbage) |
| `apps/api/tests/test_webhooks.py` | Modified | Added membership.updated/deleted tests |
| `apps/api/tests/test_auth.py` | Modified | Added skip path tests |
| `apps/api/tests/test_error_codes_sync.py` | Created | Backend error code consistency |
| `apps/api/tests/test_tenant_service.py` | Created | TenantService edge cases |
| `apps/api/tests/support/__init__.py` | Created | Support package |
| `apps/api/tests/support/factories.py` | Created | LeadFactory data factory |

---

## Coverage Impact

| Area | Before | After |
|------|--------|-------|
| Webhook handlers tested | 2/6 event types | 4/6 event types |
| Auth skip paths tested | 1/4 public paths | 4/4 public paths |
| Error code sync verified | 0 source locations | 3 source locations |
| TenantService edge cases | 0 tests | 4 tests |
| Data factory pattern | None | LeadFactory established |

---

## Notes

- Contract tests (`test_contracts.py`) remain skipped — they require a running API server
- E2E tests (`tests/e2e/`) remain mostly skipped — they require Clerk test fixtures
- Frontend tests (`apps/web/`) were already well-covered (23 passing) — no changes needed
- This session fixed the corrupted `test_constants.py` from a previous session's failed writes
