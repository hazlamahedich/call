# Test Quality Pre-Generation Checklist

Complete this checklist before writing any test suite. Every item MUST pass.

---

## Structure & Naming

- [ ] **BDD naming**: Every test follows `test_{given}_{when}_{then}` pattern
- [ ] **Traceability ID**: Every test has `[X.X-UNIT-XXX]` or `[X.X-AC-XXX]` comment
- [ ] **No hardcoded waits**: Zero `time.sleep()` or `await asyncio.sleep()` except explicit timeout tests
- [ ] **Factory functions**: All test data uses factory/builders, never inline dict literals

## Isolation & Cleanup

- [ ] **No shared mutable state**: Each test creates its own data
- [ ] **Cleanup hooks**: Fixtures tear down data even on failure
- [ ] **Singleton reset**: All global singletons (TTS orchestrator, cache, LLM) reset in autouse fixture
- [ ] **Database rollback**: Tests use transaction rollback or dedicated test DB

## Coverage

- [ ] **Happy path**: At least 1 test for the primary success scenario
- [ ] **Edge cases**: Empty input, None/missing fields, boundary values
- [ ] **Error paths**: Invalid input raises correct exception with correct code
- [ ] **Tenant isolation**: org_id scoping tested for all multi-tenant operations

## Assertions

- [ ] **Specific assertions**: Assert exact values, not just "truthy" or "exists"
- [ ] **No catch-all**: No bare `except Exception` in test code
- [ ] **Error code checks**: When testing errors, assert both status code AND error code
- [ ] **No implementation coupling**: Tests verify behavior, not internal method names

## Performance & Reliability

- [ ] **Deterministic**: Test produces same result on every run
- [ ] **No external dependencies**: No real API calls, file system paths, or network access
- [ ] **Reasonable timeout**: Test completes in < 5 seconds
- [ ] **No order dependency**: Test passes regardless of execution order

## Cache-Specific (when applicable)

- [ ] **Cache invalidation**: Test verifies cache is cleared on mutation events
- [ ] **Cache key scope**: Test verifies cache keys include org_id where applicable
- [ ] **TTL behavior**: Test verifies expired cache entries are not served

---

_Apply this checklist to every story's test suite before marking story as complete._
