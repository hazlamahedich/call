"""
[2.3-UNIT-004] Test TTS orchestrator recovery specifics.
"""

import pytest
import time
from unittest.mock import AsyncMock, MagicMock

from services.tts.base import TTSResponse, TTSProviderBase
from services.tts.orchestrator import TTSOrchestrator, SessionTTSState
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


def _mock_provider(name: str, *, latency_ms: float = 100.0, error: bool = False):
    p = MagicMock(spec=TTSProviderBase)
    p.provider_name = name
    p.synthesize = AsyncMock(
        return_value=TTSResponse(
            audio_bytes=b"" if error else b"audio",
            latency_ms=latency_ms,
            provider=name,
            content_type="" if error else "audio/mpeg",
            error=error,
            error_message="error" if error else None,
        )
    )
    return p


def _mock_session():
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_make_result())
    session.flush = AsyncMock()
    return session


class TestRecoveryPromotion:
    """
    [2.3-UNIT-004_P0] Given fallback provider is active and healthy,
    when 5 consecutive healthy responses and cooldown elapsed,
    then promote back to primary.
    """

    @pytest.mark.asyncio
    async def test_promote_after_five_healthy(self):
        settings = _make_settings(TTS_RECOVERY_COOLDOWN_SEC=0)
        primary = _mock_provider("elevenlabs", latency_ms=100)
        fallback = _mock_provider("cartesia", latency_ms=80)
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )
        session = _mock_session()

        orchestrator._session_state["vci-rec"] = SessionTTSState(
            active_provider="cartesia",
            last_switch_at=0,
        )

        for _ in range(5):
            await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id="vci-rec",
                org_id="org-1",
                text="hi",
                voice_id="v1",
            )

        assert orchestrator.get_session_provider("vci-rec") == "elevenlabs"

    @pytest.mark.asyncio
    async def test_recovery_counter_resets_on_slow_response(self):
        settings = _make_settings(TTS_RECOVERY_COOLDOWN_SEC=0)
        primary = _mock_provider("elevenlabs", latency_ms=100)
        fallback = _mock_provider("cartesia", latency_ms=80)

        slow_fallback = MagicMock(spec=TTSProviderBase)
        slow_fallback.provider_name = "cartesia"
        call_count = [0]

        async def _synth(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 3:
                return TTSResponse(
                    audio_bytes=b"audio",
                    latency_ms=400,
                    provider="cartesia",
                    content_type="audio/mpeg",
                )
            return TTSResponse(
                audio_bytes=b"audio",
                latency_ms=80,
                provider="cartesia",
                content_type="audio/mpeg",
            )

        slow_fallback.synthesize = AsyncMock(side_effect=_synth)

        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": slow_fallback},
            app_settings=settings,
        )
        session = _mock_session()

        orchestrator._session_state["vci-rst"] = SessionTTSState(
            active_provider="cartesia",
            last_switch_at=0,
        )

        for _ in range(4):
            await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id="vci-rst",
                org_id="org-1",
                text="hi",
                voice_id="v1",
            )

        state = orchestrator._session_state["vci-rst"]
        assert state.recovery_healthy_count < 5
        assert orchestrator.get_session_provider("vci-rst") == "cartesia"


class TestRecoveryDisabled:
    """
    [2.3-UNIT-004_P1] Given TTS_AUTO_RECOVERY_ENABLED is False,
    when fallback is healthy, then no promotion occurs.
    """

    @pytest.mark.asyncio
    async def test_recovery_disabled_by_config(self):
        settings = _make_settings(
            TTS_AUTO_RECOVERY_ENABLED=False, TTS_RECOVERY_COOLDOWN_SEC=0
        )
        primary = _mock_provider("elevenlabs", latency_ms=100)
        fallback = _mock_provider("cartesia", latency_ms=80)
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )
        session = _mock_session()

        orchestrator._session_state["vci-dis"] = SessionTTSState(
            active_provider="cartesia",
            last_switch_at=0,
        )

        for _ in range(10):
            await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id="vci-dis",
                org_id="org-1",
                text="hi",
                voice_id="v1",
            )

        assert orchestrator.get_session_provider("vci-dis") == "cartesia"


class TestRecoveryCooldown:
    """
    [2.3-UNIT-004_P0] Given cooldown period has NOT elapsed since last switch,
    when recovery conditions are otherwise met, then recovery is blocked.
    """

    @pytest.mark.asyncio
    async def test_cooldown_prevents_recovery(self):
        settings = _make_settings(TTS_RECOVERY_COOLDOWN_SEC=3600)
        primary = _mock_provider("elevenlabs", latency_ms=100)
        fallback = _mock_provider("cartesia", latency_ms=80)
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )
        session = _mock_session()

        orchestrator._session_state["vci-cd"] = SessionTTSState(
            active_provider="cartesia",
            last_switch_at=time.monotonic(),
        )

        for _ in range(10):
            await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id="vci-cd",
                org_id="org-1",
                text="hi",
                voice_id="v1",
            )

        assert orchestrator.get_session_provider("vci-cd") == "cartesia"

    @pytest.mark.asyncio
    async def test_oscillation_protection(self):
        settings = _make_settings(TTS_RECOVERY_COOLDOWN_SEC=3600)
        primary = _mock_provider("elevenlabs", latency_ms=600)
        fallback = _mock_provider("cartesia", latency_ms=80)
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )
        session = _mock_session()

        for _ in range(3):
            await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id="vci-osc",
                org_id="org-1",
                text="hi",
                voice_id="v1",
            )

        assert orchestrator.get_session_provider("vci-osc") == "cartesia"

        for _ in range(10):
            await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id="vci-osc",
                org_id="org-1",
                text="hi",
                voice_id="v1",
            )

        assert orchestrator.get_session_provider("vci-osc") == "cartesia"
