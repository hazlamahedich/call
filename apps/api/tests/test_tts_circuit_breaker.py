"""
[2.3-CARRY-FORWARD] Test TTS circuit breaker — provider skipping for new sessions.
"""

import pytest
import time
from unittest.mock import AsyncMock, MagicMock

from services.tts.base import TTSResponse, TTSProviderBase
from services.tts.orchestrator import (
    TTSOrchestrator,
    TTSAllProvidersFailedError,
    SessionTTSState,
    ProviderCircuitBreaker,
)
from tests.support.mock_helpers import _make_result


def _make_settings(**overrides):
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
    error_message: str | None = None,
):
    p = MagicMock(spec=TTSProviderBase)
    p.provider_name = name
    p.synthesize = AsyncMock(
        return_value=TTSResponse(
            audio_bytes=b"" if error else b"audio",
            latency_ms=latency_ms,
            provider=name,
            content_type="" if error else "audio/mpeg",
            error=error,
            error_message=error_message,
        )
    )
    return p


def _mock_session():
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_make_result())
    session.flush = AsyncMock()
    return session


class TestCircuitBreakerUnit:
    """
    [2.3-CARRY_P0] ProviderCircuitBreaker unit tests.
    """

    def test_P0_record_fallback_trips_circuit(self):
        cb = ProviderCircuitBreaker(open_duration_sec=30, trip_threshold=3)
        for _ in range(3):
            cb.record_fallback("elevenlabs")
        assert cb.is_open("elevenlabs")

    def test_P0_no_trip_below_threshold(self):
        cb = ProviderCircuitBreaker(open_duration_sec=30, trip_threshold=3)
        cb.record_fallback("elevenlabs")
        cb.record_fallback("elevenlabs")
        assert not cb.is_open("elevenlabs")

    def test_P0_circuit_auto_closes_after_duration(self):
        cb = ProviderCircuitBreaker(open_duration_sec=0.01, trip_threshold=1)
        cb.record_fallback("elevenlabs")
        assert cb.is_open("elevenlabs")
        time.sleep(0.02)
        assert not cb.is_open("elevenlabs")

    def test_P0_record_success_resets_circuit(self):
        cb = ProviderCircuitBreaker(open_duration_sec=30, trip_threshold=1)
        cb.record_fallback("elevenlabs")
        assert cb.is_open("elevenlabs")
        cb.record_success("elevenlabs")
        assert not cb.is_open("elevenlabs")

    def test_P0_independent_per_provider(self):
        cb = ProviderCircuitBreaker(open_duration_sec=30, trip_threshold=1)
        cb.record_fallback("elevenlabs")
        assert cb.is_open("elevenlabs")
        assert not cb.is_open("cartesia")


class TestCircuitBreakerIntegration:
    """
    [2.3-CARRY_P0] Circuit breaker integrated with orchestrator — new sessions skip open providers.
    """

    @pytest.mark.asyncio
    async def test_P0_new_session_skips_open_provider(self):
        settings = _make_settings()
        primary = _mock_provider("elevenlabs", error=True, error_message="Timeout")
        fallback = _mock_provider("cartesia", latency_ms=100)
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )

        for i in range(3):
            session = _mock_session()
            await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id=f"vci-trigger-{i}",
                org_id="org-1",
                text="hello",
                voice_id="v1",
            )

        assert orchestrator._circuit_breaker.is_open("elevenlabs")

        session2 = _mock_session()
        response = await orchestrator.synthesize_for_call(
            session2,
            call_id=2,
            vapi_call_id="vci-new",
            org_id="org-1",
            text="hello",
            voice_id="v1",
        )
        assert response.provider == "cartesia"
        assert orchestrator.get_session_provider("vci-new") == "cartesia"

    @pytest.mark.asyncio
    async def test_P1_circuit_success_clears_on_healthy_response(self):
        settings = _make_settings()
        primary = _mock_provider("elevenlabs", latency_ms=100)
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary},
            app_settings=settings,
        )
        session = _mock_session()

        await orchestrator.synthesize_for_call(
            session,
            call_id=1,
            vapi_call_id="vci-healthy",
            org_id="org-1",
            text="hello",
            voice_id="v1",
        )

        cb = orchestrator._circuit_breaker
        assert not cb.is_open("elevenlabs")

    @pytest.mark.asyncio
    async def test_P1_error_fallback_trips_circuit_on_primary(self):
        settings = _make_settings()
        primary = _mock_provider("elevenlabs", error=True, error_message="Timeout")
        fallback = _mock_provider("cartesia", latency_ms=100)
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )

        for i in range(3):
            session = _mock_session()
            await orchestrator.synthesize_for_call(
                session,
                call_id=i + 1,
                vapi_call_id=f"vci-err-{i}",
                org_id="org-1",
                text="hello",
                voice_id="v1",
            )

        cb = orchestrator._circuit_breaker
        assert cb.is_open("elevenlabs")
