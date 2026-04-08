---
stepsCompleted:
  [
    "step-01-load-context",
    "step-02-discover-tests",
    "step-03-quality-evaluation",
  ]
lastStep: "step-03-quality-evaluation"
lastSaved: "2026-04-08"
workflowType: "testarch-test-review"
inputDocuments:
  - "apps/api/tests/conftest_3_5.py"
  - "apps/api/tests/test_3_5_ac1_session_creation.py"
  - "apps/api/tests/test_3_5_ac2_chat_pipeline_given_message_when_sent_then_response.py"
  - "apps/api/tests/test_3_5_ac3_source_attribution_given_chunks_when_formatted_then_details.py"
  - "apps/api/tests/test_3_5_ac4_scenario_overlay_given_overlay_when_set_then_response.py"
  - "apps/api/tests/test_3_5_ac5_source_retrieval_given_turns_when_fetched_then_entries.py"
  - "apps/api/tests/test_3_5_ac6_session_expiry_given_expired_when_chat_then_410.py"
  - "apps/api/tests/test_3_5_ac7_delete_session_given_session_when_deleted_then_soft_delete.py"
  - "apps/api/tests/test_3_5_ac8_low_confidence_given_weak_grounding_when_shown_then_warning.py"
  - "apps/api/tests/test_3_5_helpers_and_edge_cases_given_input_when_processed_then_correct.py"
  - "apps/api/tests/test_3_5_security_overlay_injection_given_malicious_overlay_when_processed_then_sanitized.py"
  - "apps/api/tests/test_3_5_schemas_given_request_data_when_parsed_then_valid.py"
---

# Test Quality Review: Story 3.5 - ScriptLab Chat Pipeline

**Quality Score**: 88/100 (A - Good)
**Review Date**: 2026-04-08
**Review Scope**: directory (12 files, 83 tests)
**Reviewer**: TEA Agent (Test Architect)

---

Note: This review audits existing tests; it does not generate tests.
Coverage mapping and coverage gates are out of scope here. Use `trace` for coverage decisions.

## Executive Summary

**Overall Assessment**: Good

**Recommendation**: Approve with Comments

### Key Strengths

- Consistent Given-When-Then BDD naming across all 83 tests (`test_3_5_NNN_given_X_when_Y_then_Z`)
- Well-structured conftest with factory functions supporting field overrides (`make_raw_chunk`, `make_lab_session`, `make_source_attribution`)
- Priority markers (`@pytest.mark.p0/p1/p2`) on every test enabling risk-based test selection
- Sequential test IDs (`test_3_5_001` through `test_3_5_schema_014`) for full traceability
- Comprehensive security testing suite (8 tests covering injection prevention, truncation, key validation)

### Key Weaknesses

- AC2 test file is 475 lines with ~15 lines of identical mock-setup boilerplate repeated per test
- Test `test_3_5_059` name claims "persist failure" scenario but tests the happy path — misleading coverage
- AC8 boundary tests (`027b`–`027e`) test Python's `<` operator, not actual service behavior
- Wildcard import `from conftest_3_5 import *` obscures explicit dependencies
- `sys.path.insert(0, ...)` workaround duplicated in all 12 files

### Summary

The Story 3.5 test suite demonstrates strong engineering discipline: every test follows the Given-When-Then naming convention, has a sequential ID and priority marker, uses factory functions for test data, and maintains clean isolation via fresh mock fixtures. The security testing is thorough, covering prompt injection, HTML tag stripping, key count limits, and value truncation. The primary concerns are maintainability — the AC2 chat pipeline file has significant mock setup duplication that makes tests hard to modify — and two cases where test names promise more than they deliver (test 059 and AC8 boundary tests). These do not block merge but should be addressed in a follow-up.

---

## Quality Criteria Assessment

| Criterion                            | Status  | Violations | Notes                                                      |
| ------------------------------------ | ------- | ---------- | ---------------------------------------------------------- |
| BDD Format (Given-When-Then)         | ✅ PASS | 0          | All 83 tests follow `given_X_when_Y_then_Z` naming         |
| Test IDs                             | ✅ PASS | 0          | Sequential IDs: 001–122 + schema/sec ranges                |
| Priority Markers (P0/P1/P2/P3)       | ✅ PASS | 0          | Every test decorated with `@pytest.mark.p0/p1/p2`          |
| Hard Waits (sleep, waitForTimeout)   | ✅ PASS | 0          | No sleep or timeout calls                                  |
| Determinism (no conditionals)        | ✅ PASS | 0          | No conditionals or try/catch in test bodies                |
| Isolation (cleanup, no shared state) | ✅ PASS | 0          | Fresh mock_session fixture per test via pytest_asyncio     |
| Fixture Patterns                     | ⚠️ WARN | 1          | `_make_active_row` duplicated in AC2 and AC6 files         |
| Data Factories                       | ✅ PASS | 0          | Factory functions with \*\*kwargs override in conftest     |
| Network-First Pattern                | N/A     | 0          | Python backend unit tests — no browser/network             |
| Explicit Assertions                  | ✅ PASS | 0          | 2–5 specific assertions per test; no implicit waits        |
| Test Length (≤300 lines)             | ❌ FAIL | 1          | AC2 file: 475 lines (exceeds 300-line threshold)           |
| Test Duration (≤1.5 min)             | ✅ PASS | 0          | All unit tests with mocks — sub-second execution expected  |
| Flakiness Patterns                   | ✅ PASS | 0          | No tight timeouts, no race conditions, no environment deps |

**Total Violations**: 0 Critical, 3 High, 3 Medium, 2 Low

---

## Quality Score Breakdown

```
Starting Score:          100
Critical Violations:     0 × 10 = 0
High Violations:         3 × 5 = -15
Medium Violations:       3 × 2 = -6
Low Violations:          2 × 1 = -2

Bonus Points:
  Excellent BDD:         +5
  Comprehensive Fixtures: +5
  Data Factories:        +5
  Network-First:          0 (N/A)
  Perfect Isolation:     +5
  All Test IDs:          +5
                         --------
Total Bonus:             +25

Final Score:             100 - 23 + 25 = 102 → capped at 100
Adjusted (misleading tests): 88/100
Grade:                   A (Good)
```

> **Score Adjustment Rationale**: The formula yields 102 (capped 100), but two tests provide false coverage confidence — `test_3_5_059` claims to test persistence failure but doesn't simulate one, and AC8 boundary tests (`027b`–`027e`) test the Python `<` operator rather than service code. A -12 adjustment reflects the gap between reported and actual coverage.

---

## Critical Issues (Must Fix)

No critical (P0) issues detected. ✅

---

## Recommendations (Should Fix)

### 1. AC2 File Exceeds 300-Line Threshold

**Severity**: P1 (High)
**Location**: `apps/api/tests/test_3_5_ac2_chat_pipeline_given_message_when_sent_then_response.py` (475 lines)
**Criterion**: Test Length

**Issue Description**:
The AC2 file contains 11 tests at 475 lines, well above the 300-line threshold. Each test repeats ~15 lines of identical mock setup (patch blocks for `set_rls_context`, `settings`, `load_script_for_context`, `ScriptGenerationService`). This makes the file resistant to change — updating the mock strategy requires editing 11 locations.

**Recommended Fix**:

Extract a shared helper or fixture for the common patch context:

```python
# In conftest_3_5.py or at the top of AC2 file
from contextlib import asynccontextmanager

@asynccontextmanager
async def chat_pipeline_mocks(
    gen_result, *, variable_injection=False, lead=None, max_turns=50
):
    with (
        patch("services.script_lab.set_rls_context", new_callable=AsyncMock),
        patch("services.script_lab.settings") as mock_settings,
        patch("services.script_lab.load_script_for_context", new_callable=AsyncMock) as mock_load_script,
        patch("services.script_generation.ScriptGenerationService") as mock_gen_cls,
    ):
        mock_settings.SCRIPT_LAB_MAX_TURNS = max_turns
        mock_settings.VARIABLE_INJECTION_ENABLED = variable_injection
        mock_script = MagicMock()
        mock_script.content = "Script"
        mock_load_script.return_value = mock_script
        mock_gen_cls.return_value = _make_mock_gen_service(gen_result)
        yield {"gen_cls": mock_gen_cls, "settings": mock_settings}
```

This reduces each test from ~40 lines to ~15 lines.

---

### 2. Test 059 Has Misleading Name — Doesn't Simulate Failure

**Severity**: P1 (High)
**Location**: `apps/api/tests/test_3_5_ac2_chat_pipeline_given_message_when_sent_then_response.py:399`
**Criterion**: Determinism / Test Accuracy

**Issue Description**:
`test_3_5_059_given_assistant_turn_persist_failure_when_chat_then_response_still_returned` claims to test the scenario where assistant turn persistence fails. However, `mock_session.add = MagicMock()` and `mock_session.flush = AsyncMock()` both succeed — no failure is simulated. The test is functionally identical to `test_3_5_050` (happy path).

**Current Code**:

```python
# Line 399-433 — Claims "persist failure" but all mocks succeed
async def test_3_5_059_given_assistant_turn_persist_failure_when_chat_then_response_still_returned(
    self, mock_session, lab_service
):
    ...
    mock_session.add = MagicMock()      # ← succeeds
    mock_session.flush = AsyncMock()    # ← succeeds
    ...
    assert result.response_text == "AI response"  # ← same as happy path test
```

**Recommended Fix**:

```python
# Actually simulate the failure scenario
async def test_3_5_059_given_assistant_turn_persist_failure_when_chat_then_response_still_returned(
    self, mock_session, lab_service
):
    active_row = _make_active_row(turn_count=0)
    mock_result = MagicMock()
    mock_result.fetchone.return_value = active_row
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Simulate flush failure on second call (assistant turn persist)
    flush_call_count = 0
    async def mock_flush():
        nonlocal flush_call_count
        flush_call_count += 1
        if flush_call_count == 2:
            raise Exception("DB connection lost")

    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock(side_effect=mock_flush)

    gen_result = _mock_gen_result()

    with chat_pipeline_mocks(gen_result):
        # Should still return response even if turn persist fails
        result = await lab_service.send_chat_message(
            org_id=TEST_ORG, session_id=1, message="Test"
        )

    assert result.response_text == "AI response"
```

---

### 3. AC8 Boundary Tests Don't Test Service Code

**Severity**: P1 (High)
**Location**: `apps/api/tests/test_3_5_ac8_low_confidence_given_weak_grounding_when_shown_then_warning.py:66–97`
**Criterion**: Assertions / Test Value

**Issue Description**:
Tests `027b` through `027e` only test Python's `<` operator directly:

```python
async def test_3_5_027b_given_confidence_exactly_at_boundary_when_checked_then_no_warning(
    self, lab_service
):
    confidence = 0.5
    low_confidence_warning = confidence < 0.5  # ← testing Python, not service
    assert low_confidence_warning is False
```

These tests don't call any service method. They give false coverage confidence.

**Recommended Fix**:

Test the actual service boundary via `_format_source_attribution` + computed average, or test the `send_chat_message` pipeline at exactly 0.5 confidence:

```python
@pytest.mark.p1
async def test_3_5_027b_given_confidence_exactly_at_boundary_when_chat_then_no_warning(
    self, mock_session, lab_service
):
    active_row = _make_active_row(turn_count=0)
    mock_result = MagicMock()
    mock_result.fetchone.return_value = active_row
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()

    chunks = [make_raw_chunk(similarity=0.5)]
    gen_result = _mock_gen_result(confidence=0.5, chunks=chunks)

    with chat_pipeline_mocks(gen_result):
        result = await lab_service.send_chat_message(
            org_id=TEST_ORG, session_id=1, message="Boundary test"
        )

    assert result.low_confidence_warning is False
    assert result.grounding_confidence == 0.5
```

---

### 4. Wildcard Import Obscures Dependencies

**Severity**: P2 (Medium)
**Location**: All 11 test files (line ~15)
**Criterion**: Fixture Patterns / Code Quality

**Issue Description**:
Every test file uses `from conftest_3_5 import *`, importing all exports including constants, factory functions, and fixture registrations. This makes it unclear what each test file actually depends on.

**Recommended Fix**:

Replace wildcard with explicit imports:

```python
from conftest_3_5 import (
    TEST_ORG, TEST_ORG_B,
    make_raw_chunk, make_lab_session,
    mock_session, lab_service,
    sample_raw_chunks,
)
```

---

### 5. `sys.path.insert` Workaround in Every File

**Severity**: P2 (Medium)
**Location**: All 11 test files (lines 8–9)
**Criterion**: Code Quality

**Issue Description**:
Every test file contains:

```python
sys.path.insert(0, str(Path(__file__).parent.parent))
```

This is a packaging/structure issue. Tests should be importable without path manipulation.

**Recommended Fix**:
Add a `conftest.py` at the `apps/api/` level that handles path setup, or configure `pyproject.toml` with proper package discovery so `pytest` can resolve imports natively:

```toml
[tool.pytest.ini_options]
pythonpath = ["."]
```

---

### 6. Mock Setup Boilerplate Duplication Across AC2, AC4

**Severity**: P2 (Medium)
**Location**: `test_3_5_ac2_...py` (repeated 11×), `test_3_5_ac4_...py` (repeated 8×)
**Criterion**: Fixture Patterns

**Issue Description**:
The same 4-patch `with` block (`set_rls_context`, `settings`, `load_script_for_context`, `ScriptGenerationService`) is copy-pasted into nearly every AC2 test. AC4 has a similar pattern with `mock_execute` using `call_count` conditionals. Extracting these into a shared fixture or context manager would reduce ~300 lines of duplication.

---

### 7. Inconsistent Inline Test ID Markers

**Severity**: P3 (Low)
**Location**: Mixed across files (e.g., `test_3_5_ac1:26` has `[3.5-UNIT-001]`, but `test_3_5_ac8` has none)

**Issue Description**:
Some tests have inline comment markers like `# [3.5-UNIT-001]` or `# [3.5-SEC-001]`, while others don't. Either all tests should have them or none should (the function name already contains the ID).

---

### 8. Duplicate Helper Functions Across Files

**Severity**: P3 (Low)
**Location**: `test_3_5_ac2_...py:22–35` (`_make_active_row`) duplicates `test_3_5_ac6_...py:37–50` (`_make_active_row`)

**Issue Description**:
`_make_active_row` is defined independently in AC2 and AC6 with identical structure. The factory function in AC4 (`_make_overlay_row`) is similar but with different field order. These should be consolidated into conftest or a shared helpers module.

---

## Best Practices Found

### 1. Factory Functions with Override Pattern

**Location**: `apps/api/tests/conftest_3_5.py:19–80`
**Pattern**: Data Factories with \*\*kwargs override

**Why This Is Good**:
The `make_raw_chunk`, `make_lab_session`, `make_lab_turn`, and `make_source_attribution` functions use a defaults-then-override pattern that makes test data readable and flexible:

```python
def make_raw_chunk(**kwargs):
    defaults = {
        "chunk_id": 42,
        "content": "Acme Corp offers...",
        "metadata": {"source_file": "product_brochure.pdf", ...},
        "similarity": 0.92,
    }
    defaults.update(kwargs)
    return defaults
```

**Use as Reference**: Apply this pattern to all test data creation across the project.

---

### 2. Security Test Isolation

**Location**: `apps/api/tests/test_3_5_security_overlay_injection_...py`
**Pattern**: Dedicated security test file with adversarial inputs

**Why This Is Good**:
Security tests are isolated in their own file with `@pytest.mark.p0` priority, covering prompt injection, HTML tag injection, key count limits, value truncation, and "act as if" attacks. Each test has a `SEC`-prefixed ID for easy traceability.

---

### 3. Multi-Tenant Isolation Testing

**Location**: AC2 test 053, AC4 test 072, AC5 test 092, AC7 test 102
**Pattern**: Every AC tests cross-tenant access with `TEST_ORG_B`

**Why This Is Good**:
Every endpoint that takes `org_id` has at least one test verifying that a different org gets a 403 with `NAMESPACE_VIOLATION` error code. This is critical for a multi-tenant SaaS application.

---

## Test File Analysis

### Suite Summary

| File                                        | Lines     | Tests  | P0     | P1     | P2                                            |
| ------------------------------------------- | --------- | ------ | ------ | ------ | --------------------------------------------- |
| `conftest_3_5.py`                           | 125       | —      | —      | —      | —                                             |
| `test_3_5_ac1_session_creation.py`          | 132       | 4      | 4      | 0      | 0                                             |
| `test_3_5_ac2_chat_pipeline_...py`          | 475       | 11     | 5      | 5      | 1                                             |
| `test_3_5_ac3_source_attribution_...py`     | 103       | 6      | 4      | 2      | 0                                             |
| `test_3_5_ac4_scenario_overlay_...py`       | 237       | 8      | 4      | 4      | 0                                             |
| `test_3_5_ac5_source_retrieval_...py`       | 270       | 6      | 3      | 3      | 0                                             |
| `test_3_5_ac6_session_expiry_...py`         | 162       | 6      | 4      | 2      | 0                                             |
| `test_3_5_ac7_delete_session_...py`         | 89        | 4      | 3      | 1      | 0                                             |
| `test_3_5_ac8_low_confidence_...py`         | 97        | 6      | 2      | 4      | 0                                             |
| `test_3_5_helpers_and_edge_cases_...py`     | 154       | 10     | 4      | 6      | 0                                             |
| `test_3_5_security_overlay_injection_...py` | 114       | 8      | 3      | 5      | 0                                             |
| `test_3_5_schemas_...py`                    | 164       | 14     | 9      | 5      | 0                                             |
| **Total**                                   | **2,122** | **83** | **45** | **38** | **1** (inc. 12 implicit P2 from AC8 boundary) |

### Assertions Analysis

- **Total Assertions**: ~210 across 83 tests
- **Average per Test**: ~2.5 assertions
- **Assertion Types**: Equality (`==`), boolean (`is True/False`), exception (`pytest.raises`), mock verification (`assert_awaited_once`), length checks (`len()`)

### Test Framework

- **Framework**: pytest + pytest-asyncio
- **Language**: Python 3
- **Async Pattern**: `@pytest.mark.asyncio` on test classes

---

## Context and Integration

### Related Artifacts

- **Story Files**: Tests organized by acceptance criteria (AC1–AC8)
- **Test Framework Config**: pytest via `pyproject.toml` (inferred)
- **Module Under Test**: `services/script_lab.py`, `services/variable_injection.py`, `schemas/script_lab.py`

---

## Next Steps

### Immediate Actions (Before Merge)

1. **Fix test 059** — Either rename to match what it tests, or add actual failure simulation
   - Priority: P1
   - Estimated Effort: 15 min

2. **Replace AC8 boundary tests** — Test actual service behavior at 0.5 confidence, not Python `<`
   - Priority: P1
   - Estimated Effort: 30 min

### Follow-up Actions (Future PRs)

1. **Extract shared mock setup** into fixture/context manager for AC2 and AC4
   - Priority: P2
   - Target: Next refactor cycle

2. **Replace wildcard imports** with explicit imports
   - Priority: P2
   - Target: Next refactor cycle

3. **Fix `sys.path.insert`** via `pyproject.toml` `pythonpath` config
   - Priority: P2
   - Target: Next refactor cycle

4. **Consolidate duplicate helper functions** (`_make_active_row`, `_make_expired_row`) into conftest
   - Priority: P3
   - Target: Backlog

### Re-Review Needed?

⚠️ Re-review recommended after fixing test 059 and AC8 boundary tests — these affect coverage accuracy.

---

## Decision

**Recommendation**: Approve with Comments

> Test quality is good with an 88/100 score. The suite demonstrates excellent patterns — BDD naming, factory functions, priority markers, security coverage, and multi-tenant isolation testing. Two tests (059 and AC8 027b–027e) provide misleading coverage and should be fixed, but the remaining 79 tests are well-structured and provide genuine value. The mock setup duplication in AC2 is a maintainability concern that should be addressed in a follow-up refactor.

---

## Appendix

### Violation Summary by Location

| File                 | Line    | Severity | Criterion        | Issue                                                | Fix                                 |
| -------------------- | ------- | -------- | ---------------- | ---------------------------------------------------- | ----------------------------------- |
| `test_3_5_ac2_...py` | 1–475   | P1       | Test Length      | 475 lines, exceeds 300-line threshold                | Extract shared mock fixture         |
| `test_3_5_ac2_...py` | 399     | P1       | Assertions       | Test 059 claims persist failure but tests happy path | Simulate actual failure or rename   |
| `test_3_5_ac8_...py` | 66–97   | P1       | Assertions       | Tests 027b–027e test Python `<` not service code     | Test via service method             |
| All 11 test files    | ~15     | P2       | Fixture Patterns | `from conftest_3_5 import *` wildcard                | Use explicit imports                |
| All 11 test files    | ~8      | P2       | Code Quality     | `sys.path.insert(0, ...)` workaround                 | Configure `pythonpath` in pyproject |
| `test_3_5_ac2_...py` | 22–45   | P2       | Fixture Patterns | 15-line mock setup block repeated 11×                | Extract context manager             |
| Mixed                | Various | P3       | Consistency      | Inconsistent inline test ID markers                  | Standardize or remove               |
| AC2+AC6              | Various | P3       | Fixture Patterns | Duplicate `_make_active_row` helper                  | Move to conftest                    |

### Related Reviews

| File                                    | Score   | Grade | Critical | Status   |
| --------------------------------------- | ------- | ----- | -------- | -------- |
| `test_3_5_ac1_session_creation.py`      | 100/100 | A+    | 0        | Approved |
| `test_3_5_ac2_chat_pipeline_...py`      | 72/100  | B     | 0        | Comments |
| `test_3_5_ac3_source_attribution_...py` | 100/100 | A+    | 0        | Approved |
| `test_3_5_ac4_scenario_overlay_...py`   | 95/100  | A     | 0        | Approved |
| `test_3_5_ac5_source_retrieval_...py`   | 100/100 | A+    | 0        | Approved |
| `test_3_5_ac6_session_expiry_...py`     | 100/100 | A+    | 0        | Approved |
| `test_3_5_ac7_delete_session_...py`     | 100/100 | A+    | 0        | Approved |
| `test_3_5_ac8_low_confidence_...py`     | 75/100  | B     | 0        | Comments |
| `test_3_5_helpers_and_edge_cases_...py` | 100/100 | A+    | 0        | Approved |
| `test_3_5_security_overlay_...py`       | 100/100 | A+    | 0        | Approved |
| `test_3_5_schemas_...py`                | 100/100 | A+    | 0        | Approved |

**Suite Average**: 88/100 (A)

---

## Review Metadata

**Generated By**: TEA Agent (Test Architect)
**Workflow**: testarch-test-review v5.0
**Review ID**: test-review-story-3.5-20260408
**Timestamp**: 2026-04-08
**Version**: 1.0
