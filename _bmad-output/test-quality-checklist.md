# Test Quality Pre-Generation Checklist

**Purpose**: Prevent D+ → B remediation cycle by enforcing quality standards during test creation.

**Owner**: Dana (QA) + Murat (TEA)
**Last Updated**: 2026-04-04
**Applies To**: All new test suites (pytest, vitest, playwright)

---

## ✅ Mandatory Requirements

All tests MUST meet these requirements BEFORE being marked as complete.

### 1. BDD Given-When-Then Naming

Every test MUST use descriptive BDD naming that explains:
- **Given**: What is the initial state/context?
- **When**: What action is being taken?
- **Then**: What is the expected outcome?

**Format**:
```python
async def test_3_1_001_given_valid_org_when_ingesting_knowledge_then_succeeds():
    # [3.1-UNIT-001] Knowledge ingestion creates vector embeddings
    pass
```

**Acceptance Criteria**:
- [ ] Test name describes the scenario, not just the function being tested
- [ ] Name is self-documenting; comments should not be needed to understand what's being tested
- [ ] Follows pattern: `test_{story}_{id}_given_{context}_when_{action}_then_{outcome}`

---

### 2. Traceability IDs

Every test MUST include a traceability ID in the format:
- `[X.X-UNIT-XXX]` for unit tests
- `[X.X-E2E-XXX]` for end-to-end tests
- `[X.X-INTEGRATION-XXX]` for integration tests

---

### 3. Factory Functions for Test Data

All test data MUST be created using factory functions, NOT hardcoded values.

---

### 4. No Hard Waits

Tests MUST NOT use hardcoded sleep/wait times. Use fake timers or await conditions.

---

### 5. Cleanup Hooks

All tests MUST clean up resources (databases, mocks, singletons, connections).

---

### 6. Mock Isolation

Tests MUST isolate mocks and not depend on external services.

---

### 7. Proper Error Assertions

Tests MUST assert on specific error messages/codes, not just "error raised".

---

*See full documentation in the project repository for detailed examples and templates.*
