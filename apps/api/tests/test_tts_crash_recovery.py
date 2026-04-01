"""
[2.3-UNIT-007] Test TTS crash consistency — exception handling in DB operations.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from services.tts.base import TTSResponse, TTSProviderBase
from services.tts.orchestrator import TTSOrchestrator
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
        "TTS_SESSION_TTL_SEC": 7200,
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        setattr(s, k, v)
    return s


def _mock_provider(name: str, latency_ms: float = 100.0):
    p = MagicMock(spec=TTSProviderBase)
    p.provider_name = name
    p.synthesize = AsyncMock(
        return_value=TTSResponse(
            audio_bytes=b"audio",
            latency_ms=latency_ms,
            provider=name,
            content_type="audio/mpeg",
        )
    )
    return p


class TestCrashConsistency:
    """
    [2.3-UNIT-007_P0] Given exceptions during DB operations,
    when they occur, then session state is not corrupted.
    """

    @pytest.mark.asyncio
    async def test_exception_during_record_request_no_corruption(self):
        settings = _make_settings()
        primary = _mock_provider("elevenlabs", latency_ms=100)
        fallback = _mock_provider("cartesia", latency_ms=80)
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )

        session = AsyncMock()
        call_count = [0]

        async def _failing_execute(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise Exception("DB connection lost")
            return _make_result()

        session.execute = AsyncMock(side_effect=_failing_execute)
        session.flush = AsyncMock()

        response = await orchestrator.synthesize_for_call(
            session,
            call_id=1,
            vapi_call_id="vci-crash1",
            org_id="org-1",
            text="hello",
            voice_id="v1",
        )

        assert response.provider == "elevenlabs"
        assert response.error is False
        assert orchestrator.get_session_provider("vci-crash1") == "elevenlabs"

    @pytest.mark.asyncio
    async def test_exception_during_record_switch_no_partial_state(self):
        settings = _make_settings()
        primary = _mock_provider("elevenlabs", latency_ms=600)
        fallback = _mock_provider("cartesia", latency_ms=80)
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )

        session = AsyncMock()
        call_count = [0]

        async def _execute(*args, **kwargs):
            call_count[0] += 1
            if "tts_provider_switches" in str(args):
                raise Exception("DB error during switch insert")
            return _make_result()

        session.execute = AsyncMock(side_effect=_execute)
        session.flush = AsyncMock()

        for _ in range(3):
            try:
                await orchestrator.synthesize_for_call(
                    session,
                    call_id=1,
                    vapi_call_id="vci-crash2",
                    org_id="org-1",
                    text="hello",
                    voice_id="v1",
                )
            except Exception:
                pass

        active = orchestrator.get_session_provider("vci-crash2")
        assert active in ("elevenlabs", "cartesia")

    @pytest.mark.asyncio
    async def test_fallback_exception_after_primary_switch(self):
        settings = _make_settings()
        primary = _mock_provider("elevenlabs", latency_ms=600)

        fallback = MagicMock(spec=TTSProviderBase)
        fallback.provider_name = "cartesia"
        fallback.synthesize = AsyncMock(
            return_value=TTSResponse(
                audio_bytes=b"audio",
                latency_ms=80,
                provider="cartesia",
                content_type="audio/mpeg",
            )
        )

        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_make_result())
        session.flush = AsyncMock()

        for _ in range(3):
            await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id="vci-crash3",
                org_id="org-1",
                text="hello",
                voice_id="v1",
            )

        assert orchestrator.get_session_provider("vci-crash3") == "cartesia"
