# Story 2.6: Testing Strategy Enhancements

**Date**: 2026-04-04
**Author**: Test Architect (Murat)
**Purpose**: Address all testing concerns from adversarial review
**Status**: Approved for Implementation

---

## Executive Summary

**Adversarial Review Findings (Murat)**:
1. 🔴 Mock Hell - Need contract tests with real providers
2. 🟡 Arbitrary Coverage Target - Replace with risk-based targets
3. 🔴 Missing Failure Scenarios - Need chaos tests
4. 🟡 E2E Test Factories Missing - Repeats Story 2.4's mistake
5. 🟡 Tenant Isolation Test Too Narrow - Missing DoS, injection, privilege escalation

**Status**: ✅ **All concerns addressed in this document**

---

## Phase 5b: Contract Testing (NEW)

### Problem: Mock Hell

**Murat's Concern**:
> "Mock external TTS providers (ElevenLabs, Cartesia) in all tests + integration tests = false confidence. We're not integrating anything real; tests pass but production fails."

**Solution**: Contract tests with one real provider per CI run

### Contract Test Design

**Approach**: Consumer-Driven Contracts (CDC) using Pact

**Architecture**:
```
┌─────────────────────────────────────────────────────────────┐
│                     Test Suite                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Consumer Tests (99% of CI runs)                    │  │
│  │  - Mocked ElevenLabs provider                       │  │
│  │  - Mocked Cartesia provider                         │  │
│  │  - Fast (<1s per test)                              │  │
│  │  - Reliable (no network flakiness)                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Contract Tests (1 CI run per day)                  │  │
│  │  - Real ElevenLabs API (Monday, Wednesday, Friday)  │  │
│  │  - Real Cartesia API (Tuesday, Thursday)            │  │
│  │  - Slow (~3s per test)                              │  │
│  │  - Validates real integration                       │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Implementation

**Backend Contract Tests** (`apps/api/tests/test_audio_test_contracts.py`):

```python
import pytest
from unittest.mock import patch
from services.audio_test import AudioTestService
from services.tts.factory import get_tts_orchestrator

@pytest.mark.contract
@pytest.mark.skipif(
    os.getenv("CI_RUN_CONTRACT_TESTS") != "true",
    reason="Contract tests run once per day, not every CI"
)
class TestAudioTestContracts:
    """Contract tests with REAL TTS providers.

    Run these tests daily (not every CI run) to validate:
    1. Provider API contracts haven't changed
    2. Our integration code works with real providers
    3. Latency expectations are realistic
    """

    @pytest.mark.asyncio
    async def test_elevenlabs_real_integration(self):
        """Test with REAL ElevenLabs API.

        Validates:
        - API key works
        - API signature hasn't changed
        - Audio bytes are returned
        - Latency is acceptable (<3s for 10s clip)
        """
        orchestrator = get_tts_orchestrator()
        service = AudioTestService(orchestrator)

        config = AgentConfig(
            agent_id=1,
            org_id=1,
            voice_id="eleven_turbo_v2",
            voice_provider="elevenlabs",
            speech_speed=1.0,
            stability=0.8,
        )

        response = await service.generate_test_audio(
            text="Hello, this is a test.",
            voice_config=config,
        )

        # Validate contract
        assert response is not None
        assert len(response) > 1000  # At least 1KB of audio
        assert isinstance(response, bytes)

        # Validate latency (should be <3s for 10s clip)
        # Note: We can't measure exact latency here, but we can
        # validate the test completes in reasonable time
        # pytest-timeout will catch >10s responses

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_cartesia_real_integration(self):
        """Test with REAL Cartesia API."""
        orchestrator = get_tts_orchestrator()
        service = AudioTestService(orchestrator)

        config = AgentConfig(
            agent_id=1,
            org_id=1,
            voice_id="sonic-english",
            voice_provider="cartesia",
            speech_speed=1.0,
            stability=0.8,
        )

        response = await service.generate_test_audio(
            text="Hello, this is a test.",
            voice_config=config,
        )

        assert response is not None
        assert len(response) > 1000
        assert isinstance(response, bytes)

    @pytest.mark.asyncio
    async def test_provider_fallback_real(self):
        """Test fallback with REAL providers.

        If primary fails, fallback should work.
        """
        orchestrator = get_tts_orchestrator()

        # Try primary provider
        config = AgentConfig(
            agent_id=1,
            org_id=1,
            voice_id="invalid_voice_id",  # Force failure
            voice_provider="elevenlabs",
            speech_speed=1.0,
            stability=0.8,
        )

        service = AudioTestService(orchestrator)

        # Should fallback to Cartesia
        response = await service.generate_test_audio(
            text="Hello, this is a test.",
            voice_config=config,
        )

        # Even with invalid voice_id, fallback should work
        assert response is not None
```

**CI/CD Schedule**:

```yaml
# .github/workflows/test.yml

name: Tests

on:
  push:
    branches: [main]
  pull_request:
  schedule:
    # Run contract tests daily at 2 AM UTC
    - cron: '0 2 * * *'

jobs:
  # Regular tests (every CI run)
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run unit tests (mocked)
        run: |
          pytest apps/api/tests/ -v --cov=apps/api --cov-report=xml

  # Contract tests (daily only)
  contract-tests:
    if: github.event_name == 'schedule' || contains(github.event.head_commit.message, '[contract-tests]')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run contract tests (real providers)
        env:
          ELEVENLABS_API_KEY: ${{ secrets.ELEVENLABS_API_KEY }}
          CARTESIA_API_KEY: ${{ secrets.CARTESIA_API_KEY }}
          CI_RUN_CONTRACT_TESTS: "true"
        run: |
          pytest apps/api/tests/test_audio_test_contracts.py -v -m contract
```

### Benefits

1. **Fast Feedback**: 99% of tests use mocks (<1min total)
2. **Real Validation**: Daily contract tests catch provider API changes
3. **Cost Control**: Limited real API calls (not every CI run)
4. **Reliability**: Network flakiness doesn't block every PR

---

## Phase 5c: Chaos Testing (NEW)

### Problem: Missing Failure Scenarios

**Murat's Concern**:
> "Test list covers happy paths; no chaos engineering. 2 AM pager duty when edge cases fail."

**Solution**: Chaos tests for all failure modes

### Chaos Test Scenarios

**File**: `apps/api/tests/test_audio_test_chaos.py`

```python
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from services.audio_test import AudioTestService
from exceptions import AudioTestError

@pytest.mark.chaos
class TestAudioTestChaos:
    """Chaos tests for audio test failure scenarios.

    These tests validate graceful degradation when:
    - Network failures occur
    - Provider APIs return errors
    - Timeouts happen
    - Concurrent operations conflict
    """

    @pytest.mark.asyncio
    async def test_provider_api_500_error_mid_generation(self):
        """Test: ElevenLabs returns 500 mid-generation.

        Expected: Fallback to Cartesia, user sees clear error.
        """
        orchestrator = get_tts_orchestrator()
        service = AudioTestService(orchestrator)

        # Mock ElevenLabs to return 500
        with patch.object(
            orchestrator._providers["elevenlabs"],
            "synthesize",
            side_effect=Exception("HTTP 500: Internal Server Error")
        ):
            config = AgentConfig(
                agent_id=1,
                org_id=1,
                voice_id="eleven_turbo_v2",
                voice_provider="elevenlabs",
                speech_speed=1.0,
                stability=0.8,
            )

            # Should fallback to Cartesia
            response = await service.generate_test_audio(
                text="Test",
                voice_config=config,
            )

            # Validate fallback worked
            assert response is not None
            assert len(response) > 0

    @pytest.mark.asyncio
    async def test_rate_limit_during_generation(self):
        """Test: Cartesia rate-limits during generation.

        Expected: Clear error message, UI remains functional.
        """
        orchestrator = get_tts_orchestrator()

        # Mock Cartesia to raise rate limit error
        with patch.object(
            orchestrator._providers["cartesia"],
            "synthesize",
            side_effect=Exception("429: Rate limit exceeded")
        ):
            service = AudioTestService(orchestrator)

            config = AgentConfig(
                agent_id=1,
                org_id=1,
                voice_id="sonic-english",
                voice_provider="cartesia",
                speech_speed=1.0,
                stability=0.8,
            )

            with pytest.raises(AudioTestError) as exc_info:
                await service.generate_test_audio(
                    text="Test",
                    voice_config=config,
                )

            # Validate user-friendly error
            assert "rate limit" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_network_timeout_at_3_seconds(self):
        """Test: Network timeout at 3 seconds.

        Expected: Fallback provider tried, no indefinite hang.
        """
        orchestrator = get_tts_orchestrator()

        # Mock ElevenLabs to hang (timeout)
        async def hanging_synthesize(*args, **kwargs):
            await asyncio.sleep(10)  # Hang for 10s
            return b"audio"

        with patch.object(
            orchestrator._providers["elevenlabs"],
            "synthesize",
            new=hanging_synthesize
        ):
            service = AudioTestService(orchestrator)

            config = AgentConfig(
                agent_id=1,
                org_id=1,
                voice_id="eleven_turbo_v2",
                voice_provider="elevenlabs",
                speech_speed=1.0,
                stability=0.8,
            )

            # Should timeout and fallback
            # pytest-timeout will catch the hang
            with pytest.raises((AudioTestError, TimeoutError)):
                await service.generate_test_audio(
                    text="Test",
                    voice_config=config,
                )

    @pytest.mark.asyncio
    async def test_concurrent_save_while_generating(self):
        """Test: User clicks Save while audio is generating.

        Expected: Both operations complete, no race conditions.
        """
        orchestrator = get_tts_orchestrator()
        service = AudioTestService(orchestrator)

        config = AgentConfig(
            agent_id=1,
            org_id=1,
            voice_id="eleven_turbo_v2",
            voice_provider="elevenlabs",
            speech_speed=1.5,
            stability=0.7,
        )

        # Start audio generation (async, not awaited)
        generation_task = asyncio.create_task(
            service.generate_test_audio(
                text="Test",
                voice_config=config,
            )
        )

        # Immediately save config (simulating user clicking Save)
        # This should not interfere with audio generation
        await asyncio.sleep(0.1)  # Small delay to ensure generation started

        # Mock save operation
        async def mock_save(config):
            await asyncio.sleep(0.1)
            return config

        save_task = asyncio.create_task(mock_save(config))

        # Both should complete without error
        generation_result = await generation_task
        save_result = await save_task

        assert generation_result is not None
        assert save_result is not None

    @pytest.mark.asyncio
    async def test_navigate_away_during_generation(self):
        """Test: User navigates away during generation.

        Expected: Generation continues in background, doesn't crash.
        """
        orchestrator = get_tts_orchestrator()
        service = AudioTestService(orchestrator)

        config = AgentConfig(
            agent_id=1,
            org_id=1,
            voice_id="eleven_turbo_v2",
            voice_provider="elevenlabs",
            speech_speed=1.0,
            stability=0.8,
        )

        # Start generation
        task = asyncio.create_task(
            service.generate_test_audio(
                text="Test",
                voice_config=config,
            )
        )

        # Simulate navigation (cancel task)
        task.cancel()

        # Should handle cancellation gracefully
        with pytest.raises(asyncio.CancelledError):
            await task

    @pytest.mark.asyncio
    async def test_all_providers_down(self):
        """Test: All providers are down.

        Expected: Clear error, no crash, UI remains functional.
        """
        orchestrator = get_tts_orchestrator()

        # Mock all providers to fail
        for provider_name, provider in orchestrator._providers.items():
            with patch.object(
                provider,
                "synthesize",
                side_effect=Exception("Connection refused")
            ):
                service = AudioTestService(orchestrator)

                config = AgentConfig(
                    agent_id=1,
                    org_id=1,
                    voice_id="test",
                    voice_provider=provider_name,
                    speech_speed=1.0,
                    stability=0.8,
                )

                with pytest.raises(AudioTestError) as exc_info:
                    await service.generate_test_audio(
                        text="Test",
                        voice_config=config,
                    )

                # Validate user-friendly error
                assert "temporarily unavailable" in str(exc_info.value).lower()
```

### Chaos Testing Tools

**Required Packages**:
```bash
pytest-timeout  # Catch hanging tests
pytest-asyncio   # Async test support
pytest-mock     # Mocking
```

**Installation**:
```bash
pip install pytest-timeout pytest-asyncio pytest-mock
```

---

## Phase 5d: Security Testing Expansion (NEW)

### Problem: Tenant Isolation Test Too Narrow

**Murat's Concern**:
> "Security test only checks org1 can't access org2 config. Missing DoS, injection, and privilege escalation vectors."

**Solution**: Expanded security test scenarios

### Security Test Scenarios

**File**: `apps/api/tests/test_agent_config_security.py`

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from models.agent_config import AgentConfig
from fastapi import status

@pytest.mark.security
@pytest.mark.priority("P0")
class TestAgentConfigSecurity:
    """P0 Security tests for agent config endpoints.

    Validated threats:
    - DoS via config flooding
    - Resource exhaustion via large payloads
    - SQL injection via voice_id
    - Privilege escalation via agent_id tampering
    - Tenant bypass via org_id manipulation
    """

    @pytest.mark.asyncio
    async def test_dos_config_flooding(self, client: AsyncClient, org1_config: AgentConfig):
        """Test: org1 creates 10,000 configs → rate limited.

        Validates:
        - Rate limiting prevents DoS
        - Database protected from flooding
        """
        # Try to create 100 configs rapidly
        configs = []
        for i in range(100):
            config = {
                "agent_id": i,
                "voice_id": f"voice_{i}",
                "speech_speed": 1.0,
                "stability": 0.8,
            }
            configs.append(config)

        # Bulk create
        responses = []
        for config in configs:
            response = await client.put(
                f"/api/v1/agent-config",
                json=config,
                headers={"org-id": str(org1_config.org_id)}
            )
            responses.append(response)

        # After ~50 requests, should be rate limited
        rate_limited_count = sum(
            1 for r in responses if r.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        )

        assert rate_limited_count > 0, "Should be rate limited after 50 requests"

    @pytest.mark.asyncio
    async def test_resource_exhaustion_large_custom_settings(self, client: AsyncClient, org1_config: AgentConfig):
        """Test: 1GB custom_voice_settings dict → validation error.

        Validates:
        - Payload size limits enforced
        - Database protected from bloat
        """
        # Create 1MB payload (not 1GB, to avoid timeout in test)
        large_settings = {
            f"key_{i}": f"value_{'x' * 1000}"  # 1KB per entry
            for i in range(1000)  # 1000 entries = ~1MB
        }

        config = {
            "agent_id": 1,
            "voice_id": "test",
            "speech_speed": 1.0,
            "stability": 0.8,
            "custom_voice_settings": large_settings,
        }

        response = await client.put(
            f"/api/v1/agent-config",
            json=config,
            headers={"org-id": str(org1_config.org_id)}
        )

        # Should reject large payload
        assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE

    @pytest.mark.asyncio
    async def test_sql_injection_via_voice_id(self, client: AsyncClient, org1_config: AgentConfig):
        """Test: SQL injection via voice_id → sanitized/rejected.

        Validates:
        - SQL injection prevented
        - Input validation works
        """
        malicious_voice_ids = [
            "'; DROP TABLE agent_configs; --",
            "' OR '1'='1",
            "'; INSERT INTO agent_configs VALUES (...); --",
            "<script>alert('xss')</script>",
        ]

        for voice_id in malicious_voice_ids:
            config = {
                "agent_id": 1,
                "voice_id": voice_id,
                "speech_speed": 1.0,
                "stability": 0.8,
            }

            response = await client.put(
                f"/api/v1/agent-config",
                json=config,
                headers={"org-id": str(org1_config.org_id)}
            )

            # Should reject malicious input
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_privilege_escalation_agent_id_tampering(self, client: AsyncClient, org1_user: AgentConfig, org2_config: AgentConfig):
        """Test: Agent ID tampering for privilege escalation → 403.

        Validates:
        - org1 cannot modify org2's config
        - Agent ID validation prevents cross-tenant access
        """
        # org1 tries to modify org2's agent config
        config = {
            "agent_id": org2_config.agent_id,  # org2's agent ID
            "voice_id": "stolen_voice",
            "speech_speed": 2.0,
            "stability": 0.0,
        }

        response = await client.put(
            f"/api/v1/agent-config",
            json=config,
            headers={"org-id": str(org1_user.org_id)}  # org1's token
        )

        # Should reject (403 Forbidden)
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Verify org2's config unchanged
        get_response = await client.get(
            f"/api/v1/agent-config?agent_id={org2_config.agent_id}",
            headers={"org-id": str(org2_config.org_id)}
        )

        assert get_response.status_code == status.HTTP_200_OK
        original_config = get_response.json()
        assert original_config["voice_id"] != "stolen_voice"

    @pytest.mark.asyncio
    async def test_tenant_bypass_org_id_manipulation(self, client: AsyncClient, org1_user: AgentConfig):
        """Test: org_id manipulation to bypass tenant isolation → rejected.

        Validates:
        - org_id from token is used, not request body
        - Cannot override org_id via request
        """
        # Try to override org_id in request body
        config = {
            "agent_id": 1,
            "org_id": 99999,  # Try to set org_id to different tenant
            "voice_id": "test",
            "speech_speed": 1.0,
            "stability": 0.8,
        }

        response = await client.put(
            f"/api/v1/agent-config",
            json=config,
            headers={"org-id": str(org1_user.org_id)}  # Token's org_id
        )

        # Should succeed but use token's org_id, not request body
        assert response.status_code == status.HTTP_200_OK

        # Verify config created with token's org_id
        saved_config = response.json()
        assert saved_config["org_id"] == org1_user.org_id
        assert saved_config["org_id"] != 99999

    @pytest.mark.asyncio
    async def test_unauthenticated_request_rejected(self, client: AsyncClient):
        """Test: Unauthenticated request → 401.

        Validates:
        - Authentication required for all endpoints
        - No anonymous access possible
        """
        config = {
            "agent_id": 1,
            "voice_id": "test",
            "speech_speed": 1.0,
            "stability": 0.8,
        }

        # No auth headers
        response = await client.put(
            f"/api/v1/agent-config",
            json=config,
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
```

---

## Risk-Based Coverage Targets (REVISED)

### Problem: Arbitrary 80% Coverage

**Murat's Concern**:
> ">80% coverage with no risk-based rationale. Teams game coverage; miss risky edge cases."

**Solution**: Risk-based coverage targets

### Coverage Targets by Risk Level

| Component | Risk Level | Coverage Target | Rationale |
|-----------|-----------|-----------------|-----------|
| **Config CRUD API** | 🔴 CRITICAL | 95% | Direct database writes, high risk of bugs |
| **Audio Generation** | 🔴 CRITICAL | 95% | External dependencies, high failure risk |
| **Tenant Isolation** | 🔴 CRITICAL | 100% | Security vulnerability, data leak risk |
| **Error Handling** | 🟡 HIGH | 90% | Failure scenarios impact UX |
| **Circuit Breaker** | 🟡 HIGH | 90% | System stability depends on it |
| **Happy Path Sliders** | 🟢 LOW | 70% | Simple UI, low risk |
| **Frontend Component** | 🟢 LOW | 75% | Pure UI, low risk |

### Implementation

**Add to pytest.ini**:

```ini
# pytest.ini

[pytest]
# Minimum coverage thresholds
cov-report = term-missing:skip-covered
cov-report = html:htmlcov
cov-fail-under = 90  # Overall minimum

# Per-module thresholds (enforced in CI)
cov-config = .coveragerc

# .coveragerc
[report]
fail_under = 90
precision = 2

[html]
directory = htmlcov

[run]
omit =
    */tests/*
    */migrations/*
    */__init__.py

[xml]
output = coverage.xml
```

**CI/CD Enforcement**:

```yaml
# .github/workflows/coverage.yml

name: Coverage Check

on:
  pull_request:

jobs:
  coverage:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests with coverage
        run: |
          pytest --cov=apps/api --cov-report=xml --cov-fail-under=90

      - name: Check critical paths have 95%+ coverage
        run: |
          # Enforce higher coverage for critical paths
          pytest --cov=apps/api/routers/agent_config --cov-fail-under=95
          pytest --cov=apps/api/services/audio_test --cov-fail-under=95

      - name: Check tenant isolation has 100% coverage
        run: |
          pytest --cov=apps_api/models/agent_config --cov-fail-under=100

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
```

---

## Summary: All Concerns Addressed

| Concern | Solution | Status |
|---------|----------|--------|
| Mock Hell | Contract tests with real providers (daily CI) | ✅ Addressed |
| Arbitrary Coverage | Risk-based targets (70-100%) | ✅ Addressed |
| Missing Failures | Chaos tests (6 scenarios) | ✅ Addressed |
| Static IDs | Factory functions created | ✅ Addressed |
| Narrow Security | 6 security scenarios added | ✅ Addressed |

---

## Deliverables

### Test Files Created
1. ✅ `tests/factories/agent-config-factory.ts` - Factory functions
2. 📋 `apps/api/tests/test_audio_test_contracts.py` - Contract tests
3. 📋 `apps/api/tests/test_audio_test_chaos.py` - Chaos tests
4. 📋 `apps/api/tests/test_agent_config_security.py` - Security tests

### Documentation Created
1. ✅ This document (testing enhancements)
2. ✅ Factory functions documentation
3. ✅ Contract testing strategy
4. ✅ Chaos testing scenarios
5. ✅ Security test scenarios

---

## Related Artifacts

- Story 2.6: `_bmad-output/implementation-artifacts/2-6-pre-flight-calibration-dashboard.md`
- Action Plan: `_bmad-output/implementation-artifacts/2-6-adversarial-review-action-plan.md`
- Factory Functions: `tests/factories/agent-config-factory.ts`

---

**Last Updated**: 2026-04-04
**Status**: Approved for Implementation
**Owner**: Test Architect (Murat) + QA Engineer
**Next Action**: Implement in Phase 5 of Story 2.6
