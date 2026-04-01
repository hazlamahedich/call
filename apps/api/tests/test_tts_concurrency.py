"""
[2.3-UNIT-006] Test TTS concurrency — no cross-session state leakage.
"""

import asyncio
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
        "TTS_SESSION_TTL_SEC": 3600,
        "TTS_CIRCUIT_OPEN_SEC": 30,
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        setattr(s, k, v)
    return s


def _mock_session():
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_make_result())
    session.flush = AsyncMock()
    return session


def _make_variable_provider(name: str, latency_map: dict[str, float]):
    provider = MagicMock(spec=TTSProviderBase)
    provider.provider_name = name

    async def _synth(text, voice_id, model=None):
        latency = latency_map.get(text, 100.0)
        return TTSResponse(
            audio_bytes=b"audio",
            latency_ms=latency,
            provider=name,
            content_type="audio/mpeg",
        )

    provider.synthesize = AsyncMock(side_effect=_synth)
    return provider


class TestConcurrentSessions:
    """
    [2.3-UNIT-006_P0] Given 10+ parallel sessions with mixed latencies,
    when processed concurrently, then no cross-session state leakage.
    """

    @pytest.mark.asyncio
    async def test_parallel_sessions_no_cross_leakage(self):
        settings = _make_settings()
        latency_map = {}
        for i in range(12):
            session_id = f"session-{i}"
            if i % 3 == 0:
                latency_map[session_id] = 600.0
            else:
                latency_map[session_id] = 100.0

        provider = _make_variable_provider("elevenlabs", latency_map)
        fallback = _make_variable_provider("cartesia", {"default": 80.0})
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": provider, "cartesia": fallback},
            app_settings=settings,
        )

        async def _run_session(session_idx: int):
            session = _mock_session()
            vci = f"vci-concurrent-{session_idx}"
            text = f"session-{session_idx}"

            for _ in range(4):
                await orchestrator.synthesize_for_call(
                    session,
                    call_id=session_idx,
                    vapi_call_id=vci,
                    org_id="org-1",
                    text=text,
                    voice_id="v1",
                )

        tasks = [_run_session(i) for i in range(12)]
        await asyncio.gather(*tasks)

        for i in range(12):
            vci = f"vci-concurrent-{i}"
            active = orchestrator.get_session_provider(vci)
            if i % 3 == 0:
                assert active == "cartesia", f"Session {i} should have fallen back"
            else:
                assert active == "elevenlabs", f"Session {i} should stay on primary"

    @pytest.mark.asyncio
    async def test_concurrent_fallback_triggers_correct_switches(self):
        settings = _make_settings()
        primary = MagicMock(spec=TTSProviderBase)
        primary.provider_name = "elevenlabs"

        call_counter = {"count": 0}

        async def _primary_synth(text, voice_id, model=None):
            call_counter["count"] += 1
            return TTSResponse(
                audio_bytes=b"audio",
                latency_ms=600.0,
                provider="elevenlabs",
                content_type="audio/mpeg",
            )

        primary.synthesize = AsyncMock(side_effect=_primary_synth)

        fallback = MagicMock(spec=TTSProviderBase)
        fallback.provider_name = "cartesia"
        fallback.synthesize = AsyncMock(
            return_value=TTSResponse(
                audio_bytes=b"audio",
                latency_ms=80.0,
                provider="cartesia",
                content_type="audio/mpeg",
            )
        )

        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )

        async def _run(idx):
            session = _mock_session()
            vci = f"vci-cft-{idx}"
            for _ in range(4):
                await orchestrator.synthesize_for_call(
                    session,
                    call_id=idx,
                    vapi_call_id=vci,
                    org_id="org-1",
                    text="hello",
                    voice_id="v1",
                )

        await asyncio.gather(*[_run(i) for i in range(5)])

        for i in range(5):
            assert orchestrator.get_session_provider(f"vci-cft-{i}") == "cartesia"
