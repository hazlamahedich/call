"""
[2.4-INT-004] Test Epic 4 circuit breaker across sessions.

Tests the circuit breaker behavior across different call sessions:
- Tripped circuit causes new sessions to skip provider
- Circuit recovery after cooldown allows retry
- Circuit breaker state persists across get_or_create_session calls
- Circuit breaker resets on success after cooldown
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

from services.tts.orchestrator import (
    TTSOrchestrator,
    ProviderCircuitBreaker,
)
from services.tts.base import TTSResponse, TTSProviderBase
from tests.support.mock_helpers import _make_result


def _make_settings(**overrides):
    """Helper to create mock settings with test overrides."""
    s = MagicMock()
    defaults = {
        "TTS_PRIMARY_PROVIDER": "elevenlabs",
        "TTS_FALLBACK_PROVIDER": "cartesia",
        "TTS_LATENCY_THRESHOLD_MS": 500,
        "TTS_CONSECUTIVE_SLOW_THRESHOLD": 3,
        "TTS_AUTO_RECOVERY_ENABLED": True,
        "TTS_RECOVERY_HEALTHY_COUNT": 5,
        "TTS_RECOVERY_LATENCY_MS": 300,
        "TTS_RECOVERY_COOLDOWN_SEC": 60,
        "TTS_SESSION_TTL_SEC": 3600,
        "TTS_CIRCUIT_OPEN_SEC": 30,
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        setattr(s, k, v)
    return s


def _mock_provider(
    name: str,
    *,
    latency_ms: float = 100.0,
    error: bool = False,
):
    """Helper to create a mock TTS provider."""
    p = MagicMock(spec=TTSProviderBase)
    p.provider_name = name
    p.synthesize = AsyncMock(
        return_value=TTSResponse(
            audio_bytes=b"audio",
            latency_ms=latency_ms,
            provider=name,
            content_type="audio/mpeg",
            error=error,
            error_message=None if not error else "Provider error",
        )
    )
    p.health_check = AsyncMock(return_value=True)
    p.aclose = AsyncMock()
    return p


def _mock_session():
    """Helper to create a mock DB session."""
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_make_result())
    session.flush = AsyncMock()
    return session


class TestCircuitBreakerTrippedBehavior:
    """
    [2.4-INT-004_P0] Test tripped circuit causes new sessions to skip provider.
    """

    @pytest.mark.asyncio
    async def test_tripped_circuit_skips_provider_for_new_session(self):
        """
        [2.4-INT-004_P0_S1] Given the circuit breaker is tripped for ElevenLabs
        (3+ session-level fallbacks),
        when a new call session is created,
        then the orchestrator skips ElevenLabs and starts on Cartesia.
        """
        settings = _make_settings(TTS_CIRCUIT_OPEN_SEC=10)  # Long cooldown for testing
        primary = _mock_provider("elevenlabs", latency_ms=600)
        fallback = _mock_provider("cartesia", latency_ms=100)
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )
        session = _mock_session()

        # Manually trip the circuit breaker by recording 3 fallbacks
        orchestrator._circuit_breaker.record_fallback("elevenlabs")
        orchestrator._circuit_breaker.record_fallback("elevenlabs")
        orchestrator._circuit_breaker.record_fallback("elevenlabs")

        # Verify circuit is now tripped
        assert orchestrator._circuit_breaker.is_open("elevenlabs")

        # New session should skip ElevenLabs and use Cartesia
        new_vapi_call_id = "vapi-new-session"
        result = await orchestrator.synthesize_for_call(
            session,
            call_id=99,
            vapi_call_id=new_vapi_call_id,
            org_id="org-1",
            text="new session request",
            voice_id="v1",
        )

        # Verify new session uses Cartesia (not ElevenLabs)
        assert orchestrator.get_session_provider(new_vapi_call_id) == "cartesia"
        assert result.provider == "cartesia"


class TestCircuitRecovery:
    """
    [2.4-INT-004_P0] Test circuit recovery after cooldown.
    """

    @pytest.mark.asyncio
    async def test_circuit_recovery_after_cooldown_allows_retry(self):
        """
        [2.4-INT-004_P0_S2] Given the circuit breaker is tripped for ElevenLabs,
        when the circuit cooldown elapses,
        then the next session retries ElevenLabs.
        """
        settings = _make_settings(TTS_CIRCUIT_OPEN_SEC=1)  # 1 second cooldown
        primary = _mock_provider("elevenlabs", latency_ms=600)
        fallback = _mock_provider("cartesia", latency_ms=100)
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )
        session = _mock_session()

        # Manually trip the circuit breaker
        orchestrator._circuit_breaker.record_fallback("elevenlabs")
        orchestrator._circuit_breaker.record_fallback("elevenlabs")
        orchestrator._circuit_breaker.record_fallback("elevenlabs")

        # Verify circuit is tripped
        assert orchestrator._circuit_breaker.is_open("elevenlabs")

        # Wait for cooldown to elapse
        await asyncio.sleep(1.1)  # Slightly longer than TTS_CIRCUIT_OPEN_SEC

        # Check if circuit has closed (cooldown elapsed)
        is_still_open = orchestrator._circuit_breaker.is_open("elevenlabs")

        # After cooldown, circuit should be closed
        assert not is_still_open, "Circuit should be closed after cooldown"

        # New session should retry ElevenLabs
        new_vapi_call_id = "vapi-after-cooldown"
        result = await orchestrator.synthesize_for_call(
            session,
            call_id=100,
            vapi_call_id=new_vapi_call_id,
            org_id="org-1",
            text="retry after cooldown",
            voice_id="v1",
        )

        # Verify session starts with ElevenLabs (provider was retried)
        assert orchestrator.get_session_provider(new_vapi_call_id) == "elevenlabs"


class TestCircuitStatePersistence:
    """
    [2.4-INT-004_P0] Test circuit breaker state persists across sessions.
    """

    @pytest.mark.asyncio
    async def test_circuit_state_persists_across_sessions(self):
        """
        [2.4-INT-004_P0_S3] Given the circuit breaker is tripped,
        when multiple get_or_create_session calls occur,
        then the circuit breaker state persists across all calls.
        """
        settings = _make_settings(TTS_CIRCUIT_OPEN_SEC=10)  # Long cooldown
        primary = _mock_provider("elevenlabs", latency_ms=600)
        fallback = _mock_provider("cartesia", latency_ms=100)
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )
        session = _mock_session()

        # Manually trip the circuit
        orchestrator._circuit_breaker.record_fallback("elevenlabs")
        orchestrator._circuit_breaker.record_fallback("elevenlabs")
        orchestrator._circuit_breaker.record_fallback("elevenlabs")

        # Verify circuit is tripped
        assert orchestrator._circuit_breaker.is_open("elevenlabs")

        # Create multiple new sessions - all should skip ElevenLabs
        for i in range(5):
            vapi_call_id = f"vapi-multi-{i}"
            result = await orchestrator.synthesize_for_call(
                session,
                call_id=10 + i,
                vapi_call_id=vapi_call_id,
                org_id="org-1",
                text=f"request {i}",
                voice_id="v1",
            )

            # All should use Cartesia (skipping ElevenLabs)
            assert orchestrator.get_session_provider(vapi_call_id) == "cartesia"
            assert result.provider == "cartesia"


class TestCircuitResetOnSuccess:
    """
    [2.4-INT-004_P1] Test circuit breaker resets on success after cooldown.
    """

    @pytest.mark.asyncio
    async def test_circuit_resets_on_success_after_cooldown(self):
        """
        [2.4-INT-004_P1_S1] Given the circuit breaker is tripped,
        when cooldown elapses and a successful request occurs,
        then the circuit breaker resets to closed state.
        """
        settings = _make_settings(TTS_CIRCUIT_OPEN_SEC=1)
        primary = _mock_provider("elevenlabs", latency_ms=600)
        fallback = _mock_provider("cartesia", latency_ms=100)
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )
        session = _mock_session()

        # Manually trip the circuit
        orchestrator._circuit_breaker.record_fallback("elevenlabs")
        orchestrator._circuit_breaker.record_fallback("elevenlabs")
        orchestrator._circuit_breaker.record_fallback("elevenlabs")

        # Verify circuit is tripped
        assert orchestrator._circuit_breaker.is_open("elevenlabs")

        # Wait for cooldown
        await asyncio.sleep(1.1)

        # Make a request that will succeed (circuit should be closed now)
        # Update primary to return fast response
        primary.synthesize = AsyncMock(
            return_value=TTSResponse(
                audio_bytes=b"audio",
                latency_ms=100,  # Fast now
                provider="elevenlabs",
                content_type="audio/mpeg",
                error=False,
            )
        )

        # New session should retry ElevenLabs and succeed
        vapi_call_id = "vapi-success-reset"
        result = await orchestrator.synthesize_for_call(
            session,
            call_id=200,
            vapi_call_id=vapi_call_id,
            org_id="org-1",
            text="fast request after cooldown",
            voice_id="v1",
        )

        # Verify circuit is now closed (success was recorded)
        assert not orchestrator._circuit_breaker.is_open("elevenlabs")
        assert result.provider == "elevenlabs"
