"""
[2.3-UNIT-004-B] Additional recovery boundary and config tests.
"""

import pytest
import time
from unittest.mock import AsyncMock, MagicMock

from services.tts.base import TTSResponse, TTSProviderBase
from services.tts.orchestrator import TTSOrchestrator, SessionTTSState
from tests.support.mock_helpers import _make_result
from tests.support.factories import TTSRequestFactory, TTSProviderSwitchFactory


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


def _mock_provider(name, latency_ms=100.0):
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


def _mock_session():
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_make_result())
    session.flush = AsyncMock()
    return session


class TestRecoveryBoundaryConditions:
    """
    [2.3-UNIT-004_P0] N-1 healthy should NOT trigger recovery.
    """

    @pytest.mark.asyncio
    async def test_n_minus_1_healthy_no_recovery(self):
        settings = _make_settings(TTS_RECOVERY_COOLDOWN_SEC=0)
        primary = _mock_provider("elevenlabs", latency_ms=100)
        fallback = _mock_provider("cartesia", latency_ms=80)
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )
        session = _mock_session()

        orchestrator._session_state["vci-nm1"] = SessionTTSState(
            active_provider="cartesia",
            last_switch_at=0,
        )

        for _ in range(4):
            await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id="vci-nm1",
                org_id="org-1",
                text="hi",
                voice_id="v1",
            )

        state = orchestrator._session_state["vci-nm1"]
        assert state.recovery_healthy_count == 4
        assert orchestrator.get_session_provider("vci-nm1") == "cartesia"


class TestConfigResolutionOverrides:
    """
    [2.3-UNIT-004_P1] Agent config overrides take precedence over defaults.
    """

    @pytest.mark.asyncio
    async def test_agent_override_primary_provider(self):
        settings = _make_settings()
        primary = _mock_provider("elevenlabs", latency_ms=100)
        fallback = _mock_provider("cartesia", latency_ms=80)
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )
        session = _mock_session()

        response = await orchestrator.synthesize_for_call(
            session,
            call_id=1,
            vapi_call_id="vci-cfg",
            org_id="org-1",
            text="hi",
            voice_id="v1",
            agent_tts_config={"tts_provider": "cartesia"},
        )

        assert response.provider == "cartesia"

    @pytest.mark.asyncio
    async def test_agent_override_fallback_provider(self):
        settings = _make_settings()
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
                vapi_call_id="vci-cfg2",
                org_id="org-1",
                text="hi",
                voice_id="v1",
                agent_tts_config={"fallback_tts_provider": "cartesia"},
            )

        assert orchestrator.get_session_provider("vci-cfg2") == "cartesia"


class TestFactoryDataShapes:
    """
    [2.3-UNIT-009_P1] Verify TTSRequestFactory and TTSProviderSwitchFactory produce valid data.
    """

    def test_tts_request_factory_defaults(self):
        data = TTSRequestFactory.build()
        assert data["provider"] == "elevenlabs"
        assert data["status"] == "success"
        assert data["latency_ms"] == 250.0
        assert data["call_id"] is not None

    def test_tts_request_factory_override(self):
        data = TTSRequestFactory.build(status="error", error_message="Timeout")
        assert data["status"] == "error"
        assert data["error_message"] == "Timeout"

    def test_tts_provider_switch_factory_defaults(self):
        data = TTSProviderSwitchFactory.build()
        assert data["from_provider"] == "elevenlabs"
        assert data["to_provider"] == "cartesia"
        assert data["reason"] == "latency_threshold_exceeded"
        assert data["consecutive_slow_count"] == 3

    def test_tts_provider_switch_factory_override(self):
        data = TTSProviderSwitchFactory.build(
            from_provider="cartesia",
            to_provider="elevenlabs",
            reason="recovery_healthy",
        )
        assert data["from_provider"] == "cartesia"
        assert data["reason"] == "recovery_healthy"