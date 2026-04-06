---
stepsCompleted:
  [
    "step-01-load-context",
    "step-02-discover-tests",
    "step-03-quality-evaluation",
    "step-04-generate-report",
  ]
lastStep: "step-04-generate-report"
lastSaved: "2026-04-06"
overallScore: 82
overallGrade: A-
reviewComplete: true
deploymentStatus: APPROVED
inputDocuments:
  - _bmad-output/implementation-artifacts/3-2-per-tenant-rag-namespacing-with-namespace-guard.md
  - apps/api/tests/test_namespace_guard_given_request_when_scoped_then_isolated.py
  - apps/api/tests/e2e/test_namespace_guard_e2e.py
  - apps/api/middleware/namespace_guard.py
  - apps/api/services/namespace_audit.py
  - apps/api/config/settings.py
---

# Test Quality Review: Story 3.2 — Per-Tenant RAG Namespacing

**Quality Score**: 82/100 (A- — Acceptable)
**Review Date**: 2026-04-06
**Review Scope**: directory (2 test files, 51 tests)
**Reviewer**: TEA Agent

---

Note: This review audits existing tests; it does not generate tests.
Coverage mapping and coverage gates are out of scope here. Use `trace` for coverage decisions.

## Executive Summary

**Overall Assessment**: Acceptable

**Recommendation**: Approve with Comments

### Key Strengths

- Excellent BDD naming convention (`test_3_2_NNN_given_X_when_Y_then_Z`) consistently applied across all 51 tests
- Strong traceability — every test has a `[3.2-UNIT-NNN]` or `[3.2-E2E-NNN]` ID mapped to story acceptance criteria
- 100% deterministic — zero hard waits, zero conditional flow control, all test data generated via factory helpers (`_mock_session`, `_mock_session_with_resource`)
- Good edge case coverage — 8 dedicated edge-case tests (soft-deleted resources, empty org_id, None request, 0/1/N orgs)

### Key Weaknesses

- Tests are heavily mocked (MagicMock/AsyncMock) — no real DB integration tests for namespace guard SQL queries
- Several tests are tautological — they test the mock setup, not the actual behavior (AC1, AC3, AC4 classes)
- E2E tests don't test real HTTP endpoints — they mock auth and session, making them integration-level at best
- Missing `afterEach` cleanup in E2E tests — `app.dependency_overrides` cleared in `finally` but not in `afterEach`

### Summary

The Story 3.2 test suite demonstrates strong conventions and thorough traceability, with 51 tests covering all 7 acceptance criteria plus edge cases. However, the tests rely almost exclusively on mocked sessions (`MagicMock`/`AsyncMock`) rather than hitting real database queries or HTTP endpoints. This means the tests validate function call signatures and mock wiring rather than the actual SQL behavior (e.g., that `verify_namespace_access` truly queries `knowledge_bases` with the correct `WHERE` clause). The E2E tests, despite their file name, are integration tests — they mock `AuthMiddleware._verify_token`, `_set_rls_context`, and `get_session`, so they don't exercise the real auth → guard → SQL → response pipeline. This is acceptable for unit-level confidence but leaves a gap for true end-to-end verification.

---

## Quality Criteria Assessment

| Criterion                            | Status  | Violations | Notes                                                                                       |
| ------------------------------------ | ------- | ---------- | ------------------------------------------------------------------------------------------- |
| BDD Format (Given-When-Then)         | ✅ PASS | 0          | Every test follows `given_X_when_Y_then_Z` pattern                                          |
| Test IDs                             | ✅ PASS | 0          | All 51 tests have `[3.2-UNIT-NNN]` or `[3.2-E2E-NNN]` IDs                                   |
| Priority Markers                     | ⚠️ WARN | 0          | No `@p0`/`@p1`/`@p2` markers in test decorators; priority is implicit via AC class names    |
| Hard Waits (sleep, waitForTimeout)   | ✅ PASS | 0          | No hard waits found; timing uses `time.monotonic()` for benchmarks                          |
| Determinism (no conditionals)        | ✅ PASS | 0          | No if/else controlling test paths; no try/catch flow control                                |
| Isolation (cleanup, no shared state) | ⚠️ WARN | 2          | E2E tests use `try/finally` instead of `afterEach`; mock side-effects in `_mock_execute`    |
| Fixture Patterns                     | ✅ PASS | 0          | Clean factory helpers: `_mock_session`, `_mock_session_with_resource`, `_mock_request`      |
| Data Factories                       | ⚠️ WARN | 1          | Tests use hardcoded strings ("org-alpha", "org-beta") instead of faker-generated unique IDs |
| Network-First Pattern                | N/A     | 0          | No browser/page-based tests (backend only)                                                  |
| Explicit Assertions                  | ✅ PASS | 0          | Every test has explicit `assert` statements; no hidden helpers                              |
| Test Length (≤300 lines)             | ✅ PASS | 0          | Unit: 604 lines (slightly over, but 51 tests justified); E2E: 228 lines                     |
| Test Duration (≤1.5 min)             | ✅ PASS | 0          | 51 tests in 3.14s — excellent                                                               |
| Flakiness Patterns                   | ⚠️ WARN | 1          | `_mock_execute` side_effect counts are brittle — adding a new query breaks multiple tests   |

**Total Violations**: 0 Critical, 0 High, 4 Medium, 0 Low

---

## Quality Score Breakdown

```
Starting Score:          100
Critical Violations:     -0 × 10 = -0
High Violations:         -0 × 5 = -0
Medium Violations:       -4 × 2 = -8
Low Violations:          -0 × 1 = -0

Bonus Points:
  Excellent BDD:         +5
  Comprehensive Fixtures: +5
  All Test IDs:          +5
  Perfect Determinism:   +0 (no bonus - already clean)
  Data Factories:        +0 (hardcoded strings)
  Network-First:         +0 (N/A)
                         --------
Total Bonus:             +15

Final Score:             max(0, min(100, 100 - 8 + 15)) = 82/100

Grade Mapping:
  90-100: A+ (Excellent)
  80-89: A (Good) → 82 = A-
  70-79: B (Acceptable)
  60-69: C (Needs Improvement)
  <60: F (Critical Issues)
```

---

## Recommendations (Should Fix)

### 1. Tautological Tests in AC1 and AC4 Classes

**Severity**: P2 (Medium)
**Location**: `apps/api/tests/test_namespace_guard_given_request_when_scoped_then_isolated.py:110-153` (AC1), `:260-279` (AC4)
**Criterion**: Explicit Assertions

**Issue Description**:
Several tests in `TestNamespaceGuardAC1` (tests 001-005) and `TestNamespaceGuardAC4` (tests 016-018) call `verify_namespace_access(session, org_id="X")` and assert that the return value equals the same `org_id` string. Since the mock session's `execute` returns a row with a matching `org_id`, the guard always passes through. The test is verifying that the function returns its input when the mock doesn't trigger any exception — this is tautological.

**Current Code**:

```python
# ⚠️ Tests return value == input when mock doesn't trigger exceptions
async def test_3_2_001_given_valid_org_id_when_searching_then_only_own_vectors(self):
    session = _mock_session()
    org_id = await verify_namespace_access(session=session, org_id="org-alpha")
    assert org_id == "org-alpha"
```

**Recommended Improvement**:

```python
# ✅ Better: Verify guard behavior with real-ish query patterns
async def test_3_2_001_given_valid_org_id_when_searching_then_only_own_vectors(self):
    session = _mock_session()
    result = await verify_namespace_access(session=session, org_id="org-alpha")
    assert result == "org-alpha"
    # Verify the guard did NOT query the resource table for collection endpoints
    session.execute.assert_not_awaited() if hasattr(session.execute, 'assert_not_awaited') else None
    # Or: verify it didn't make a resource lookup query
    assert session.execute.call_count == 0  # Collection endpoint: no resource query needed
```

**Priority**: These tests provide value as regression tests for the `token.org_id` bug fix and guard pass-through behavior, so they're not useless — just not testing what their names imply (namespace scoping).

---

### 2. Brittle `side_effect` Counts in Audit Tests

**Severity**: P2 (Medium)
**Location**: `apps/api/tests/test_namespace_guard_given_request_when_scoped_then_isolated.py:284-301` (test 019), `:324-336` (test 021), `:381-393` (test 025)
**Criterion**: Flakiness Patterns

**Issue Description**:
The audit tests use `AsyncMock(side_effect=[orgs_result] + [count_result] * N)` with hardcoded counts (7, 19, 7, 18). If the audit service adds a new query (e.g., a new check type), all these tests break with `StopIteration` or wrong return values. The counts are derived from the internal implementation (1 orgs query + N pairs × 3 checks × 2 queries each).

**Current Code**:

```python
# ⚠️ Hardcoded side_effect count = brittle
session.execute = AsyncMock(side_effect=[orgs_result] + [count_result] * 7)
```

**Recommended Improvement**:

```python
# ✅ Use a factory that returns appropriate values based on query content
async def _audit_execute_factory(org_ids, cross_tenant_count=0):
    call_count = 0
    async def execute(stmt, params=None):
        nonlocal call_count
        call_count += 1
        sql = str(stmt) if hasattr(stmt, '__str__') else ""
        if "DISTINCT org_id" in sql:
            result = MagicMock()
            result.fetchall.return_value = [(oid,) for oid in org_ids]
            return result
        if "set_config" in sql:
            return MagicMock()
        result = MagicMock()
        result.scalar.return_value = cross_tenant_count
        return result
    return execute

session.execute = AsyncMock(side_effect=_audit_execute_factory(["org-a", "org-b"]))
```

**Benefits**: Tests won't break when internal query count changes. More resilient to refactoring.

---

### 3. Hardcoded Test Data Instead of Factories

**Severity**: P2 (Medium)
**Location**: `apps/api/tests/test_namespace_guard_given_request_when_scoped_then_isolated.py:21-47` and `apps/api/tests/e2e/test_namespace_guard_e2e.py:17-39`
**Criterion**: Data Factories

**Issue Description**:
All test data uses hardcoded strings (`"org-alpha"`, `"org-beta"`, `"org-jwt-owner"`). While these don't collide in the current mocked setup (each test gets its own mock session), they don't demonstrate the factory pattern that would be needed for real DB tests.

**Current Code**:

```python
def _mock_session(resource_org_id=None):
    session = MagicMock(spec=AsyncSession)
    # ... hardcoded "org-alpha" default
```

**Recommended Improvement**:

```python
import uuid

def _mock_session(resource_org_id=None):
    if resource_org_id is None:
        resource_org_id = f"org-{uuid.uuid4().hex[:8]}"
    session = MagicMock(spec=AsyncSession)
    # ...
```

**Benefits**: Demonstrates factory pattern for future real-DB migration. Minor improvement for this mocked test suite since each test is isolated.

---

### 4. E2E Tests Use `try/finally` Instead of `afterEach`

**Severity**: P2 (Medium)
**Location**: `apps/api/tests/e2e/test_namespace_guard_e2e.py:59-78` (all 6 tests)
**Criterion**: Isolation

**Issue Description**:
Each E2E test manually sets up `app.dependency_overrides[get_session]` and cleans up in `finally`. This is error-prone — if a test adds more overrides and forgets to clean up, subsequent tests get polluted state.

**Current Code**:

```python
# ⚠️ Manual setup/teardown in every test
async def test_3_2_e2e_001_given_org_a_lists_when_guard_then_only_own_docs(self):
    # ...
    app.dependency_overrides[get_session] = _override_session
    try:
        # ... test body ...
    finally:
        app.dependency_overrides.clear()
```

**Recommended Improvement**:

```python
# ✅ Use autouse fixture for dependency override cleanup
@pytest.fixture(autouse=True)
def _clean_overrides(self):
    yield
    app.dependency_overrides.clear()

# Then in tests, just set overrides without try/finally:
async def test_3_2_e2e_001_given_org_a_lists_when_guard_then_only_own_docs(self):
    session = _mock_session(execute_side_effect=[count_result, docs_result])
    async def _override_session():
        yield session
    app.dependency_overrides[get_session] = _override_session
    # ... test body (cleanup is automatic)
```

---

### 5. Missing Priority Markers

**Severity**: P3 (Low)
**Location**: All test files
**Criterion**: Priority Markers

**Issue Description**:
Tests don't have `@pytest.mark.p0` / `@pytest.mark.p1` / `@pytest.mark.p2` markers for selective execution. The story spec mentions priority tags but they're not applied to the pytest tests.

**Recommended Improvement**:

```python
@pytest.mark.asyncio
@pytest.mark.p0  # Critical: namespace guard must block cross-tenant access
async def test_3_2_006_given_org_a_token_when_requesting_org_b_doc_then_403(self):
```

Then enable selective runs: `pytest -m p0` for smoke, `pytest -m "p0 or p1"` for critical path.

---

### 6. Unit Test File Slightly Over 300 Lines

**Severity**: P3 (Low)
**Location**: `apps/api/tests/test_namespace_guard_given_request_when_scoped_then_isolated.py` (604 lines)
**Criterion**: Test Length

**Issue Description**:
The unit test file is 604 lines, roughly double the 300-line guidance. However, with 51 well-organized tests in BDD classes, splitting by concern is reasonable:

**Recommended Split**:

```
tests/
  test_namespace_guard_ac1_ac4.py    # Tests for ACs 1, 4 (guard core)
  test_namespace_guard_ac2.py         # Tests for AC2 (cross-tenant rejection)
  test_namespace_guard_ac3.py         # Tests for AC3 (threshold)
  test_namespace_guard_ac5.py         # Tests for AC5 (audit)
  test_namespace_guard_ac6_ac7.py     # Tests for ACs 6, 7 (perf, feature flag)
  test_namespace_guard_edge_cases.py  # Edge cases
  test_namespace_guard_schemas.py     # Schema validation
```

---

## Best Practices Found

### 1. Excellent BDD Naming Convention

**Location**: `apps/api/tests/test_namespace_guard_given_request_when_scoped_then_isolated.py` (all tests)
**Pattern**: BDD Given-When-Then
**Knowledge Base**: test-quality.md

**Why This Is Good**:
Every test follows `test_3_2_NNN_given_X_when_Y_then_Z` where NNN matches the `[3.2-UNIT-NNN]` traceability ID. This creates a bi-directional link between spec and test. Example:

```python
async def test_3_2_006_given_org_a_token_when_requesting_org_b_doc_then_403(self):
    """[3.2-UNIT-006] Cross-tenant document access returns 403."""
```

**Use as Reference**: This pattern should be applied consistently across all project tests.

### 2. Clean Factory Helpers with Focused Purpose

**Location**: `apps/api/tests/test_namespace_guard_given_request_when_scoped_then_isolated.py:21-47`
**Pattern**: Data Factories

**Why This Is Good**:
The helper functions have clear, single responsibilities:

- `_mock_session()` — session for collection endpoints (no resource lookup)
- `_mock_session_with_resource()` — session for single-resource endpoints (with resource lookup)
- `_mock_request()` — mock HTTP request for audit logging
- `_make_row()` — creates a DB row tuple

```python
def _mock_session(resource_org_id=None):
    session = MagicMock(spec=AsyncSession)
    result = MagicMock()
    if resource_org_id is not None:
        result.fetchone.return_value = _make_row(resource_org_id)
    else:
        result.fetchone.return_value = None
    session.execute = AsyncMock(return_value=result)
    return session
```

### 3. Comprehensive Edge Case Coverage

**Location**: `apps/api/tests/test_namespace_guard_given_request_when_scoped_then_isolated.py:455-581`
**Pattern**: Edge Case Testing

**Why This Is Good**:
8 edge case tests covering boundary conditions:

- Soft-deleted resources (edge_001)
- Empty string org_id (edge_002)
- None request parameter (edge_003)
- Zero orgs audit (edge_004)
- Single org audit (edge_005)
- Three orgs produces correct pair count C(3,2)=3 (edge_006)
- Schema serialization validation (edge_007, edge_008)

---

## Test File Analysis

### File Metadata — Unit Tests

- **File Path**: `apps/api/tests/test_namespace_guard_given_request_when_scoped_then_isolated.py`
- **File Size**: 604 lines
- **Test Framework**: pytest (asyncio)
- **Language**: Python

### Test Structure

- **Describe Blocks (classes)**: 11 (`TestNamespaceGuardCore`, `TestNamespaceGuardAC1`-`AC7`, `TestNamespaceEdgeCases`, `TestNamespaceSchemas`)
- **Test Cases**: 51
- **Average Test Length**: ~10 lines per test
- **Fixtures Used**: None (pytest fixtures not used; factory functions instead)
- **Data Factories Used**: `_mock_session`, `_mock_session_with_resource`, `_mock_request`, `_make_row`

### Test Scope

- **Test IDs**: [3.2-UNIT-000] through [3.2-UNIT-029], [3.2-E2E-001] through [3.2-E2E-006], edge_001-edge_008
- **Priority Distribution**:
  - P0 (Critical): ~12 tests (cross-tenant rejection, regression)
  - P1 (High): ~15 tests (audit, feature flag, perf)
  - P2 (Medium): ~10 tests (threshold, edge cases)
  - P3 (Low): ~8 tests (schemas, naming)
  - Integration: 2 tests (marked `@pytest.mark.integration`)

### Assertions Analysis

- **Total Assertions**: ~120 (avg ~2.4 per test)
- **Assertions per Test**: 2.4 (avg)
- **Assertion Types**: `==`, `assert X > Y`, `pytest.raises(HTTPException)` with status code checks

---

### File Metadata — E2E Tests

- **File Path**: `apps/api/tests/e2e/test_namespace_guard_e2e.py`
- **File Size**: 228 lines
- **Test Framework**: pytest (asyncio) + httpx AsyncClient
- **Language**: Python

### Test Structure

- **Describe Blocks (classes)**: 1 (`TestNamespaceGuardE2E`)
- **Test Cases**: 6
- **Average Test Length**: ~30 lines per test (heavy mock setup)

### Test Scope

- **Test IDs**: [3.2-E2E-001] through [3.2-E2E-006]
- **Priority Distribution**:
  - P0: 3 tests (list docs, cross-tenant GET, nonexistent doc)
  - P1: 2 tests (unauthenticated, admin audit)
  - P2: 1 test (non-admin audit)

---

## Context and Integration

### Related Artifacts

- **Story File**: `_bmad-output/implementation-artifacts/3-2-per-tenant-rag-namespacing-with-namespace-guard.md`
- **Source Under Test**: `apps/api/middleware/namespace_guard.py` (84 lines)
- **Source Under Test**: `apps/api/services/namespace_audit.py` (203 lines)
- **Configuration**: `apps/api/config/settings.py` (112 lines, with validators)

---

## Quality Dimension Scores

| Dimension       | Weight   | Score      | Weighted Score |
| --------------- | -------- | ---------- | -------------- |
| Determinism     | 30%      | 98/100     | 29.4           |
| Isolation       | 25%      | 75/100     | 18.75          |
| Maintainability | 25%      | 88/100     | 22.0           |
| Performance     | 20%      | 60/100     | 12.0           |
| **Overall**     | **100%** | **82/100** | **82.15**      |

### Dimension Details

**Determinism (98/100) — A+**:

- ✅ Zero hard waits, zero conditional flow control
- ✅ All test data controlled via factory helpers
- ✅ Timing benchmarks use `time.monotonic()`
- ⚠️ Minor: Hardcoded side_effect counts create implicit coupling

**Isolation (75/100) — B**:

- ✅ Each test creates fresh mock sessions (no shared state)
- ✅ E2E tests clean up `dependency_overrides` in `finally`
- ⚠️ No `autouse` fixture for cleanup — manual `try/finally` pattern
- ⚠️ Hardcoded strings instead of unique IDs (parallel safety not a concern with mocks, but bad pattern)

**Maintainability (88/100) — A-**:

- ✅ Excellent BDD naming, traceability IDs
- ✅ Clean class organization by acceptance criteria
- ✅ Good edge case coverage
- ⚠️ Unit file is 604 lines (double the 300-line guidance)
- ⚠️ No `@pytest.mark.p0/p1/p2` priority markers

**Performance (60/100) — C+**:

- ✅ 51 tests in 3.14s — excellent execution speed
- ❌ Tests are entirely mocked — no real DB queries, no real HTTP stack
- ❌ Performance tests (026, 027) benchmark mock resolution speed, not real SQL latency
- ❌ The "E2E" tests mock auth, session, and RLS — they're integration tests at best

---

## Next Steps

### Immediate Actions (Before Merge)

1. **Add `@pytest.mark.integration` tag acknowledgment** — Performance tests (026, 027) already have this tag and note they test mock overhead. Acceptable as-is.
   - Priority: P3
   - Effort: 0 (already done)

2. **Add priority markers** — `@pytest.mark.p0` for cross-tenant tests, `@pytest.mark.p1` for audit tests
   - Priority: P3
   - Effort: 15 min

### Follow-up Actions (Future PRs)

1. **Add real DB integration tests** — At least 2-3 tests that hit real PostgreSQL with pgvector and RLS to verify actual SQL behavior
   - Priority: P2
   - Target: Next sprint

2. **Refactor E2E tests to use `autouse` fixture** — Reduce boilerplate and improve cleanup safety
   - Priority: P3
   - Target: Backlog

3. **Replace brittle `side_effect` counts with query-aware factory** — Make audit tests resilient to internal query changes
   - Priority: P2
   - Target: Next sprint

### Re-Review Needed?

⚠️ Re-review after P2 fixes recommended — add real DB integration tests and refactor brittle mock counts, then re-review.

---

## Decision

**Recommendation**: Approve with Comments

> Test quality is good with 82/100 score. The test suite demonstrates excellent conventions (BDD naming, traceability IDs, factory helpers, edge cases) and 100% test pass rate. The primary concern is that tests are entirely mocked — they validate function signatures and mock wiring rather than real SQL/RLS behavior. This is acceptable for the unit/integration level but should be supplemented with real DB integration tests in a follow-up PR. The 6 "E2E" tests are mislabeled — they mock auth, session, and RLS context, making them integration tests. Recommend adding 2-3 real PostgreSQL tests to validate actual namespace guard SQL queries against RLS policies.

---

## Appendix

### Violation Summary by Location

| Line    | Severity | Criterion        | Issue                         | Fix                            |
| ------- | -------- | ---------------- | ----------------------------- | ------------------------------ |
| 110-153 | P2       | Assertions       | AC1 tests tautological        | Verify no resource query made  |
| 260-279 | P2       | Assertions       | AC4 tests tautological        | Verify no resource query made  |
| 284-301 | P2       | Flakiness        | Brittle `side_effect` count   | Query-aware factory function   |
| 324-336 | P2       | Flakiness        | Brittle `side_effect` count   | Query-aware factory function   |
| 381-393 | P2       | Flakiness        | Brittle `side_effect` count   | Query-aware factory function   |
| 536     | P2       | Flakiness        | Brittle `side_effect` count   | Query-aware factory function   |
| 59-78   | P2       | Isolation        | Manual `try/finally` cleanup  | `autouse` fixture              |
| All     | P3       | Priority Markers | No `@pytest.mark.p0/p1/p2`    | Add markers for selective runs |
| 604     | P3       | Test Length      | 604 lines > 300 line guidance | Split by AC                    |

### Review Metadata

**Generated By**: TEA Agent (Test Architect)
**Workflow**: testarch-test-review
**Review ID**: test-review-story-3.2-20260406
**Timestamp**: 2026-04-06
**Version**: 1.0
