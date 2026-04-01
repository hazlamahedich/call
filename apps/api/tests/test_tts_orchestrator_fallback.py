"""
[2.3-UNIT-003] Test TTS orchestrator fallback specifics.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from services.tts.base import TTSResponse, TTSProviderBase
from services.tts.orchestrator import TTSOrchestrator, TTSAllProvidersFailedError
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


class TestFallbackThresholdBehavior:
    """
    [2.3-UNIT-003_P0] Exact threshold: 2 slow = no switch, 3 slow = switch.
    """

    @pytest.mark.asyncio
    async def test_two_slow_no_switch(self):
        settings = _make_settings()
        primary = _mock_provider("elevenlabs", latency_ms=600)
        fallback = _mock_provider("cartesia", latency_ms=100)
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )
        session = _mock_session()

        for _ in range(2):
            await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id="vci-t",
                org_id="org-1",
                text="hi",
                voice_id="v1",
            )

        assert orchestrator.get_session_provider("vci-t") == "elevenlabs"

    @pytest.mark.asyncio
    async def test_three_slow_triggers_switch(self):
        settings = _make_settings()
        primary = _mock_provider("elevenlabs", latency_ms=600)
        fallback = _mock_provider("cartesia", latency_ms=100)
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )
        session = _mock_session()

        for _ in range(3):
            await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id="vci-t2",
                org_id="org-1",
                text="hi",
                voice_id="v1",
            )

        assert orchestrator.get_session_provider("vci-t2") == "cartesia"


class TestFallbackWithAutoProvider:
    """
    [2.3-UNIT-003_P1] Given agent tts_provider is "auto",
    when primary is slow, fallback triggers.
    """

    @pytest.mark.asyncio
    async def test_auto_strategy_uses_health_system(self):
        settings = _make_settings()
        primary = _mock_provider("elevenlabs", latency_ms=600)
        fallback = _mock_provider("cartesia", latency_ms=100)
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )
        session = _mock_session()

        for _ in range(3):
            await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id="vci-auto",
                org_id="org-1",
                text="hi",
                voice_id="v1",
                agent_tts_config={"tts_provider": "auto"},
            )

        assert orchestrator.get_session_provider("vci-auto") == "cartesia"


class TestFallbackOnProviderError:
    """
    [2.3-UNIT-003_P0] Given primary returns error/timeout (not just slow),
    when fallback is healthy, then switch to fallback immediately.
    """

    @pytest.mark.asyncio
    async def test_primary_timeout_triggers_fallback(self):
        settings = _make_settings()
        primary = _mock_provider("elevenlabs", error=True, error_message="Timeout")
        fallback = _mock_provider("cartesia", latency_ms=80)
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )
        session = _mock_session()

        response = await orchestrator.synthesize_for_call(
            session,
            call_id=1,
            vapi_call_id="vci-err",
            org_id="org-1",
            text="hi",
            voice_id="v1",
        )

        assert response.provider == "cartesia"
        assert response.error is False
        assert orchestrator.get_session_provider("vci-err") == "cartesia"


class TestFallbackBoundaryConditions:
    """
    [2.3-UNIT-003_P0] Boundary: exact threshold, interleaved fast/slow.
    """

    @pytest.mark.asyncio
    async def test_exact_threshold_latency_no_fallback(self):
        settings = _make_settings(TTS_LATENCY_THRESHOLD_MS=500)
        primary = _mock_provider("elevenlabs", latency_ms=500)
        fallback = _mock_provider("cartesia", latency_ms=100)
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )
        session = _mock_session()

        for _ in range(3):
            await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id="vci-exact",
                org_id="org-1",
                text="hi",
                voice_id="v1",
            )

        assert orchestrator.get_session_provider("vci-exact") == "elevenlabs"

    @pytest.mark.asyncio
    async def test_interleaved_fast_slow_resets_counter(self):
        settings = _make_settings(TTS_CONSECUTIVE_SLOW_THRESHOLD=3)
        primary = MagicMock(spec=TTSProviderBase)
        primary.provider_name = "elevenlabs"
        call_count = [0]

        async def _synth(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] % 2 == 0:
                return TTSResponse(
                    audio_bytes=b"audio",
                    latency_ms=100,
                    provider="elevenlabs",
                    content_type="audio/mpeg",
                )
            return TTSResponse(
                audio_bytes=b"audio",
                latency_ms=600,
                provider="elevenlabs",
                content_type="audio/mpeg",
            )

        primary.synthesize = AsyncMock(side_effect=_synth)

        fallback = _mock_provider("cartesia", latency_ms=100)
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )
        session = _mock_session()

        for _ in range(6):
            await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id="vci-inter",
                org_id="org-1",
                text="hi",
                voice_id="v1",
            )

        assert orchestrator.get_session_provider("vci-inter") == "elevenlabs"

    @pytest.mark.asyncio
    async def test_self_fallback_guard_when_same_provider(self):
        settings = _make_settings(
            TTS_PRIMARY_PROVIDER="elevenlabs",
            TTS_FALLBACK_PROVIDER="elevenlabs",
        )
        primary = _mock_provider("elevenlabs", latency_ms=600)
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary},
            app_settings=settings,
        )
        session = _mock_session()

        for _ in range(3):
            await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id="vci-self",
                org_id="org-1",
                text="hi",
                voice_id="v1",
            )

        assert orchestrator.get_session_provider("vci-self") == "elevenlabs"
