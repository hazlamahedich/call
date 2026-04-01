"""
[2.3-UNIT-013] Test TTS orchestrator provider resolution — fallback logic,
voice model override, mid-range latency, no-fallback provider, emit event error.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from services.tts.base import TTSResponse, TTSProviderBase
from services.tts.orchestrator import (
    TTSOrchestrator,
    TTSAllProvidersFailedError,
    SessionTTSState,
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
    p.health_check = AsyncMock(return_value=True)
    p.aclose = AsyncMock()
    return p


def _mock_session():
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_make_result())
    session.flush = AsyncMock()
    return session


class TestProviderResolution:
    """
    [2.3-UNIT-013_P0] Edge cases in provider resolution logic.
    """

    @pytest.mark.asyncio
    async def test_P0_primary_override_not_in_providers_falls_back_to_settings(self):
        settings = _make_settings()
        primary = _mock_provider("elevenlabs", latency_ms=100)
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary},
            app_settings=settings,
        )
        session = _mock_session()

        response = await orchestrator.synthesize_for_call(
            session,
            call_id=1,
            vapi_call_id="vci-resolve",
            org_id="org-1",
            text="hello",
            voice_id="v1",
            agent_tts_config={"tts_provider": "unknown_provider"},
        )

        assert response.provider == "elevenlabs"
        assert response.error is False

    @pytest.mark.asyncio
    async def test_P0_no_providers_raises_all_failed(self):
        settings = _make_settings()
        orchestrator = TTSOrchestrator(
            providers={},
            app_settings=settings,
        )
        session = _mock_session()

        with pytest.raises(TTSAllProvidersFailedError) as exc_info:
            await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id="vci-none",
                org_id="org-1",
                text="hello",
                voice_id="v1",
            )

        assert exc_info.value.error_code == "TTS_ALL_PROVIDERS_FAILED"

    @pytest.mark.asyncio
    async def test_P0_primary_none_swaps_with_fallback(self):
        settings = _make_settings(
            TTS_PRIMARY_PROVIDER="nonexistent",
            TTS_FALLBACK_PROVIDER="cartesia",
        )
        fallback = _mock_provider("cartesia", latency_ms=100)
        orchestrator = TTSOrchestrator(
            providers={"cartesia": fallback},
            app_settings=settings,
        )
        session = _mock_session()

        response = await orchestrator.synthesize_for_call(
            session,
            call_id=1,
            vapi_call_id="vci-swap",
            org_id="org-1",
            text="hello",
            voice_id="v1",
        )

        assert response.provider == "cartesia"
        assert orchestrator.get_session_provider("vci-swap") == "cartesia"


class TestVoiceModelOverride:
    """
    [2.3-UNIT-013_P1] tts_voice_model from agent config is propagated.
    """

    @pytest.mark.asyncio
    async def test_P1_voice_model_override_passed_to_synthesize(self):
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
            vapi_call_id="vci-model",
            org_id="org-1",
            text="hello",
            voice_id="v1",
            agent_tts_config={"tts_voice_model": "eleven_turbo_v2_5"},
        )

        primary.synthesize.assert_called_once_with(
            "hello", "v1", model="eleven_turbo_v2_5"
        )


class TestMidRangeLatency:
    """
    [2.3-UNIT-013_P1] Latency between recovery and threshold resets healthy count.
    """

    @pytest.mark.asyncio
    async def test_P1_mid_range_latency_resets_recovery_healthy_count(self):
        settings = _make_settings(
            TTS_RECOVERY_LATENCY_MS=300,
            TTS_RECOVERY_COOLDOWN_SEC=0,
        )
        primary = _mock_provider("elevenlabs", latency_ms=100)
        fallback = _mock_provider("cartesia", latency_ms=80)
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )
        session = _mock_session()

        orchestrator._session_state["vci-mid"] = SessionTTSState(
            active_provider="cartesia",
            recovery_healthy_count=3,
            last_switch_at=0,
        )

        mid_provider = _mock_provider("cartesia", latency_ms=350)
        orchestrator._providers["cartesia"] = mid_provider

        await orchestrator.synthesize_for_call(
            session,
            call_id=1,
            vapi_call_id="vci-mid",
            org_id="org-1",
            text="hello",
            voice_id="v1",
        )

        state = orchestrator._session_state["vci-mid"]
        assert state.recovery_healthy_count == 0
        assert state.consecutive_slow == 0


class TestNoFallbackProvider:
    """
    [2.3-UNIT-013_P0] Primary errors with no fallback available.
    """

    @pytest.mark.asyncio
    async def test_P0_primary_error_no_fallback_raises_all_failed(self):
        settings = _make_settings()
        primary = _mock_provider(
            "elevenlabs", error=True, error_message="Connection refused"
        )
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary},
            app_settings=settings,
        )
        session = _mock_session()

        with pytest.raises(TTSAllProvidersFailedError) as exc_info:
            await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id="vci-nofb",
                org_id="org-1",
                text="hello",
                voice_id="v1",
            )

        assert (
            "no fallback" in str(exc_info.value).lower()
            or exc_info.value.error_code == "TTS_ALL_PROVIDERS_FAILED"
        )


class TestEmitVoiceEventException:
    """
    [2.3-UNIT-013_P1] _emit_voice_event exception is caught gracefully.
    """

    @pytest.mark.asyncio
    async def test_P1_voice_event_exception_does_not_crash_orchestrator(self):
        settings = _make_settings()
        primary = _mock_provider("elevenlabs", latency_ms=600)
        fallback = _mock_provider("cartesia", latency_ms=100)
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )

        session = AsyncMock()
        call_count = [0]

        async def _execute(*args, **kwargs):
            call_count[0] += 1
            if "voice_events" in str(args):
                raise RuntimeError("Voice events table missing")
            return _make_result()

        session.execute = AsyncMock(side_effect=_execute)
        session.flush = AsyncMock()

        for _ in range(3):
            await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id="vci-emiterr",
                org_id="org-1",
                text="hello",
                voice_id="v1",
            )

        assert orchestrator.get_session_provider("vci-emiterr") == "cartesia"
