---
stepsCompleted:
  [
    "step-01-load-context",
    "step-02-discover-tests",
    "step-03-quality-evaluation",
  ]
lastStep: "step-03-quality-evaluation"
lastSaved: "2026-04-09"
workflowType: "testarch-test-review"
inputDocuments:
  - "apps/api/tests/conftest_3_6.py"
  - "apps/api/tests/test_3_6_ac1_claim_extraction_given_response_when_processed_then_claims_found.py"
  - "apps/api/tests/test_3_6_ac2_self_correction_given_unsupported_when_triggered_then_corrected.py"
  - "apps/api/tests/test_3_6_ac3_correction_metadata_given_corrected_when_returned_then_fields_present.py"
  - "apps/api/services/factual_hook.py"
  - "apps/api/schemas/factual_hook.py"
---

# Test Quality Review: Story 3.6 — Factual Hook / Self-Correction

**Quality Score**: 93/100 (A — Good)
**Review Date**: 2026-04-09
**Review Scope**: directory (3 test files, 16 tests)
**Reviewer**: TEA Agent (Test Architect)

---

Note: This review audits existing tests; it does not generate tests.
Coverage mapping and coverage gates are out of scope here. Use `trace` for coverage decisions.

## Executive Summary

**Overall Assessment**: Good

**Recommendation**: Approve with Comments

### Key Strengths

- Consistent Given-When-Then BDD naming across all 16 tests (`test_3_6_NNN_given_X_when_Y_then_Z`)
- Well-designed factory functions in conftest_3_6 (`make_claim_verification`, `make_factual_hook_result`) with defaults+override pattern
- Proper class-level state cleanup in `factual_hook_service` fixture (resets `_consecutive_errors`, `_circuit_open`, `_circuit_opened_at` in yield/teardown)
- Clean mock isolation — each test receives fresh service instances with injected mocks
- Mixed test levels used appropriately — AC1 tests individual methods, AC2/AC3 test integration through `verify_and_correct`

### Key Weaknesses

- **Zero priority markers** — all 16 tests lack `@pytest.mark.p0/p1/p2/p3` despite conftest registering these markers
- **4 unused fixtures** in conftest_3_6 (`flaky_embedding_service`, `degraded_embedding_service`, `sample_claims`, `sample_knowledge_chunks`) — suggests planned but unimplemented resilience testing
- Test 001 uses a loose `any("32%" in c or "5000" in c for c in claims)` assertion that could pass with false positives
- Tests 014b/014c manually construct dicts and test `setdefault()` rather than exercising service serialization paths

### Summary

The Story 3.6 test suite is well-engineered at 16 tests across 3 files. The BDD naming is perfectly consistent, factory functions follow the established project pattern, and test isolation is thorough — the `factual_hook_service` fixture properly resets class-level mutable state in teardown. The primary concern is that the conftest defines 4 fixtures that are never referenced by any test, strongly suggesting that circuit-breaker and degraded-embedding scenarios were planned but not yet implemented. This doesn't affect the quality of the 16 existing tests but is dead code that should either be used or removed.

---

## Quality Criteria Assessment

| Criterion                            | Status  | Violations | Notes                                                      |
| ------------------------------------ | ------- | ---------- | ---------------------------------------------------------- |
| BDD Format (Given-When-Then)         | ✅ PASS | 0          | All 16 tests follow `given_X_when_Y_then_Z` naming         |
| Test IDs                             | ✅ PASS | 0          | Sequential IDs: 001–014c with b/c suffixes for additions   |
| Priority Markers (P0/P1/P2/P3)       | ❌ FAIL | 1          | Zero of 16 tests decorated with priority markers           |
| Hard Waits (sleep, waitForTimeout)   | ✅ PASS | 0          | No sleep or timeout calls                                  |
| Determinism (no conditionals)        | ✅ PASS | 0          | No conditionals or try/catch in test bodies                |
| Isolation (cleanup, no shared state) | ✅ PASS | 0          | `factual_hook_service` fixture resets class-level state    |
| Fixture Patterns                     | ⚠️ WARN | 1          | 4 unused fixtures in conftest_3_6                          |
| Data Factories                       | ✅ PASS | 0          | Factory functions with \*\*kwargs override in conftest     |
| Network-First Pattern                | N/A     | 0          | Python backend unit tests — no browser/network             |
| Explicit Assertions                  | ⚠️ WARN | 1          | Test 001 uses loose `any()` assertion                      |
| Test Length (≤300 lines)             | ✅ PASS | 0          | All 3 files well under threshold (101, 99, 156)            |
| Test Duration (≤1.5 min)             | ✅ PASS | 0          | All unit tests with mocks — sub-second execution expected  |
| Flakiness Patterns                   | ✅ PASS | 0          | No tight timeouts, no race conditions, no environment deps |

**Total Violations**: 0 Critical, 1 High, 2 Medium, 0 Low

---

## Quality Score Breakdown

```
Starting Score:          100
Critical Violations:     0 × 10 = 0
High Violations:         1 × 5 = -5
Medium Violations:       2 × 2 = -4
Low Violations:          0 × 1 = 0
                        --------
Subtotal:               100 - 9 = 91

Bonus Points:
  Excellent BDD:         +5
  Comprehensive Fixtures: +5
  Data Factories:        +5
  Perfect Isolation:     +5
  All Test IDs:          +5
                          --------
Total Bonus:             +25

Gross Score:             91 + 25 = 116 → capped at 100

Score Adjustment:        -7 (unused fixtures indicate planned-but-incomplete
                            resilience testing; loose assertion in test 001
                            could mask regressions)

Final Score:             93/100
Grade:                   A (Good)
```

> **Score Adjustment Rationale**: The formula yields 100, but 4 fixtures exist in conftest for scenarios (circuit breaker, degraded embeddings) that have zero tests. This is not a coverage penalty — it's a quality signal that the test infrastructure was built but not used. Combined with test 001's loose `any()` assertion, a -7 adjustment reflects the gap between the scaffolding present and the tests actually delivered.

---

## Critical Issues (Must Fix)

No critical (P0) issues detected. ✅

---

## Recommendations (Should Fix)

### 1. Add Priority Markers to All 16 Tests

**Severity**: P1 (High)
**Location**: All 3 test files
**Criterion**: Priority Markers

**Issue Description**:
None of the 16 tests have `@pytest.mark.p0/p1/p2/p3` decorators. The main `conftest.py` registers these markers (lines 13–16), and the Story 3.5 test suite used them on every test. Without priority markers, risk-based test selection (`pytest -m p0`) cannot filter Story 3.6 tests.

**Recommended Fix**:

```python
@pytest.mark.p0
async def test_3_6_unit_001_given_numbers_when_extracting_then_claims_found(
    self, factual_hook_service
):
    ...

@pytest.mark.p1
async def test_3_6_unit_003_given_greeting_when_extracting_then_empty(
    self, factual_hook_service
):
    ...
```

Recommended priority classification:

- **P0** (critical path): 001, 004, 005, 007, 010, 011, 013 (claim extraction, verification, correction loop, schema serialization)
- **P1** (high): 002, 003, 003b, 003c, 006, 008, 009, 012, 014 (edge cases, metadata, boundary)
- **P2** (medium): 014b, 014c (cache compatibility, backward compat)

---

### 2. Remove or Use Unused Fixtures in conftest_3_6

**Severity**: P2 (Medium)
**Location**: `apps/api/tests/conftest_3_6.py:93–140`
**Criterion**: Fixture Patterns / Dead Code

**Issue Description**:
Four fixtures are defined but never used by any test:

| Fixture                      | Lines   | Purpose                             |
| ---------------------------- | ------- | ----------------------------------- |
| `sample_claims`              | 93–99   | Returns 3 sample claim strings      |
| `sample_knowledge_chunks`    | 102–117 | Returns 2 sample knowledge chunks   |
| `flaky_embedding_service`    | 120–131 | Embedding that fails every 3rd call |
| `degraded_embedding_service` | 134–140 | Embedding that always fails         |

The `flaky_embedding_service` and `degraded_embedding_service` strongly suggest planned circuit-breaker and error-recovery tests that were never implemented.

**Recommended Fix**:

Either implement the resilience tests:

```python
@pytest.mark.p1
async def test_3_6_unit_015_given_flaky_embedding_when_verifying_then_retries(
    self, mock_session, mock_llm, flaky_embedding_service
):
    svc = FactualHookService(mock_session, mock_llm, flaky_embedding_service)
    with patch("services.factual_hook.search_knowledge_chunks",
               new_callable=AsyncMock,
               return_value=[{"chunk_id": 1, "content": "data", "similarity": 0.85}]):
        result = await svc._verify_claim("Revenue grew 32%.", "org-1", None, 0.75)
        assert result.verification_error is False
```

Or remove the unused fixtures to keep the conftest clean.

---

### 3. Tighten Test 001 Assertion

**Severity**: P2 (Medium)
**Location**: `apps/api/tests/test_3_6_ac1_...py:19–20`
**Criterion**: Explicit Assertions

**Issue Description**:
Test 001 asserts:

```python
assert len(claims) >= 1
assert any("32%" in c or "5000" in c for c in claims)
```

The `any()` check uses `or` inside, meaning a claim containing `"5000"` but NOT `"32%"` would pass — even though the response also contains `"32%"`. This is a loose assertion that could mask regressions in the quantified claim regex.

**Recommended Fix**:

```python
response = "Our revenue grew 32% in Q3. We have over 5000 active users."
claims = factual_hook_service._extract_claims(response)
assert len(claims) == 2
claim_texts = " ".join(claims)
assert "32%" in claim_texts
assert "5000" in claim_texts
```

---

## Best Practices Found

### 1. Class-Level State Cleanup in Fixture

**Location**: `apps/api/tests/conftest_3_6.py:82–90`
**Pattern**: Yield fixture with class-level mutable state reset

**Why This Is Good**:
The `factual_hook_service` fixture resets `FactualHookService` class variables both before yield and after, preventing test bleed:

```python
@pytest.fixture
def factual_hook_service(mock_session, mock_llm, mock_embedding):
    FactualHookService._consecutive_errors = 0
    FactualHookService._circuit_open = False
    FactualHookService._circuit_opened_at = 0.0
    svc = FactualHookService(mock_session, mock_llm, mock_embedding)
    yield svc
    FactualHookService._consecutive_errors = 0
    FactualHookService._circuit_open = False
    FactualHookService._circuit_opened_at = 0.0
```

This is critical for services with class-level state (circuit breaker counters) and prevents ordering-dependent failures.

---

### 2. Mixed Test Levels Used Appropriately

**Location**: AC1 (unit-level) vs AC2/AC3 (integration-level)

**Why This Is Good**:
AC1 tests target individual methods (`_extract_claims`, `_verify_claim`) with direct assertions on return values — pure unit tests. AC2 and AC3 test the `verify_and_correct` orchestration method, exercising the integration between extraction, verification, correction, and metadata assembly. This layered approach gives fast feedback at the unit level while also validating the critical end-to-end flow.

---

### 3. Progressive Scenario Testing in AC2

**Location**: `test_3_6_ac2_...py` (tests 007–010)

**Why This Is Good**:
The four AC2 tests form a complete decision matrix for the self-correction loop:

| Test | Scenario                  | Expected              |
| ---- | ------------------------- | --------------------- |
| 007  | Unsupported → correction  | LLM reprompted        |
| 008  | Corrected → passes        | Loop stops, corrected |
| 009  | Max corrections exhausted | Fallback response     |
| 010  | All supported initially   | No correction at all  |

Each test covers a distinct branch of the `verify_and_correct` algorithm with no overlap.

---

## Test File Analysis

### Suite Summary

| File                                     | Lines   | Tests  | P0    | P1    | P2    |
| ---------------------------------------- | ------- | ------ | ----- | ----- | ----- |
| `conftest_3_6.py`                        | 140     | —      | —     | —     | —     |
| `test_3_6_ac1_claim_extraction_...py`    | 101     | 6      | 0     | 0     | 0     |
| `test_3_6_ac2_self_correction_...py`     | 99      | 4      | 0     | 0     | 0     |
| `test_3_6_ac3_correction_metadata_...py` | 156     | 6      | 0     | 0     | 0     |
| **Total**                                | **496** | **16** | **0** | **0** | **0** |

> No priority markers on any test — all show 0 for P0/P1/P2 counts.

### Assertions Analysis

- **Total Assertions**: ~35 across 16 tests
- **Average per Test**: ~2.2 assertions
- **Assertion Types**: Equality (`==`), boolean (`is True/False`), membership (`in`), length checks (`len()`), mock verification (`assert_called_once`)

### Test Framework

- **Framework**: pytest + pytest-asyncio
- **Language**: Python 3
- **Async Pattern**: `@pytest.mark.asyncio` on test classes

---

## Context and Integration

### Related Artifacts

- **Source Module**: `apps/api/services/factual_hook.py` (483 lines)
- **Schema Module**: `apps/api/schemas/factual_hook.py` (27 lines)
- **Test Fixtures**: `apps/api/tests/conftest_3_6.py` (140 lines)
- **Related conftests**: `conftest_3_3.py`, `conftest_3_4.py` (imported via main `conftest.py`)

### Un tested Service Methods (For Coverage Reference)

> Note: Coverage analysis is out of scope. Listed here for context only — route to `trace` for coverage decisions.

| Method                               | Tested?     | Notes                                   |
| ------------------------------------ | ----------- | --------------------------------------- |
| `_extract_claims`                    | ✅ 4 tests  | Numbers, superlatives, greetings, mixed |
| `_verify_claim`                      | ✅ 3 tests  | Supported, unsupported, org scoping     |
| `_verify_all_claims`                 | ⬜ Indirect | Via `verify_and_correct`                |
| `verify_and_correct`                 | ✅ 5 tests  | Full loop scenarios                     |
| `_correct_response`                  | ✅ 1 test   | Reprompt assertion                      |
| `_replace_unsupported_with_fallback` | ⬜ Indirect | Via `verify_and_correct` (test 009)     |
| `_check_circuit_breaker`             | ⬜ No tests | Fixtures exist but unused               |
| `_record_error` / `_record_success`  | ⬜ No tests | Circuit breaker state management        |
| `_log_verification`                  | ⬜ No tests | Audit logging path                      |

---

## Next Steps

### Immediate Actions (Before Merge)

1. **Add priority markers** — All 16 tests need `@pytest.mark.p0/p1/p2/p3`
   - Priority: P1
   - Estimated Effort: 10 min

2. **Tighten test 001 assertion** — Replace `any()` with exact claim count and content checks
   - Priority: P2
   - Estimated Effort: 5 min

### Follow-up Actions (Future PRs)

1. **Implement or remove unused fixtures** — `flaky_embedding_service`, `degraded_embedding_service`, `sample_claims`, `sample_knowledge_chunks`
   - Priority: P2
   - Target: Same PR as circuit-breaker tests (if planned)

2. **Consider adding circuit-breaker tests** — `flaky_embedding_service` fixture suggests this was planned
   - Priority: P2
   - Target: Next sprint

3. **Refactor test 014b/014c** — Test actual serialization through the service rather than manual dict construction
   - Priority: P3
   - Target: Backlog

### Re-Review Needed?

No — the existing tests are solid. Re-review only needed if circuit-breaker tests are added.

---

## Decision

**Recommendation**: Approve with Comments

> Test quality is good at 93/100. The 16 tests demonstrate strong BDD naming, proper factory functions, excellent isolation cleanup, and a complete decision matrix for the self-correction loop. The two actionable items are: (1) add priority markers for consistency with the rest of the project, and (2) tighten the one loose assertion in test 001. The 4 unused fixtures are a housekeeping concern — they should be either wired into resilience tests or removed.

---

## Appendix

### Violation Summary by Location

| File                 | Line      | Severity | Criterion        | Issue                                        | Fix                                   |
| -------------------- | --------- | -------- | ---------------- | -------------------------------------------- | ------------------------------------- |
| All 3 test files     | All tests | P1       | Priority Markers | No `@pytest.mark.p0/p1/p2/p3` on any test    | Add priority markers                  |
| `conftest_3_6.py`    | 93–140    | P2       | Fixture Patterns | 4 fixtures defined but unused                | Implement tests or remove fixtures    |
| `test_3_6_ac1_...py` | 19–20     | P2       | Assertions       | Loose `any("32%" in c or "5000" in c)` check | Assert exact claim count and contents |

### Related Reviews

| File                                     | Score  | Grade | Critical | Status              |
| ---------------------------------------- | ------ | ----- | -------- | ------------------- |
| `test_3_6_ac1_claim_extraction_...py`    | 95/100 | A     | 0        | Approved            |
| `test_3_6_ac2_self_correction_...py`     | 95/100 | A     | 0        | Approved            |
| `test_3_6_ac3_correction_metadata_...py` | 90/100 | A-    | 0        | Approved w/ comment |

**Suite Average**: 93/100 (A)

---

## Review Metadata

**Generated By**: TEA Agent (Test Architect)
**Workflow**: testarch-test-review v5.0
**Review ID**: test-review-story-3.6-20260409
**Timestamp**: 2026-04-09
**Version**: 1.0
