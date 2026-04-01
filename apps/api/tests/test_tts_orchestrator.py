"""
[2.3-UNIT-002] Test TTS orchestrator — fallback, recovery, session management.
"""

import pytest
import time
from collections import deque
from unittest.mock import AsyncMock, MagicMock, patch

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


class TestOrchestratorFallbackTrigger:
    """
    [2.3-UNIT-002_P0] Given 3 consecutive slow responses,
    when orchestrator processes them, then it triggers fallback.
    """

    @pytest.mark.asyncio
    async def test_fallback_after_three_consecutive_slow(self):
        settings = _make_settings()
        primary = _mock_provider("elevenlabs", latency_ms=600)
        fallback = _mock_provider("cartesia", latency_ms=100)
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )
        session = _mock_session()

        for i in range(3):
            result = await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id="vci-1",
                org_id="org-1",
                text="hello",
                voice_id="v1",
            )

        assert orchestrator.get_session_provider("vci-1") == "cartesia"

    @pytest.mark.asyncio
    async def test_no_fallback_after_two_slow(self):
        settings = _make_settings()
        primary = _mock_provider("elevenlabs", latency_ms=600)
        fallback = _mock_provider("cartesia", latency_ms=100)
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )
        session = _mock_session()

        for i in range(2):
            await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id="vci-2",
                org_id="org-1",
                text="hello",
                voice_id="v1",
            )

        assert orchestrator.get_session_provider("vci-2") == "elevenlabs"

    @pytest.mark.asyncio
    async def test_fallback_resets_consecutive_slow(self):
        settings = _make_settings()
        primary = _mock_provider("elevenlabs", latency_ms=600)
        fallback = _mock_provider("cartesia", latency_ms=100)
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )
        session = _mock_session()

        for i in range(3):
            await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id="vci-3",
                org_id="org-1",
                text="hello",
                voice_id="v1",
            )

        state = orchestrator._session_state["vci-3"]
        assert state.consecutive_slow == 0


class TestOrchestratorRecovery:
    """
    [2.3-UNIT-002_P1] Given recovery conditions met, orchestrator
    promotes back to primary.
    """

    @pytest.mark.asyncio
    async def test_recovery_after_five_consecutive_healthy(self):
        settings = _make_settings(TTS_RECOVERY_COOLDOWN_SEC=0)
        primary = _mock_provider("elevenlabs", latency_ms=100)
        fallback = _mock_provider("cartesia", latency_ms=80)
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )
        session = _mock_session()

        orchestrator._session_state["vci-r1"] = SessionTTSState(
            active_provider="cartesia",
            last_switch_at=0,
        )

        for i in range(5):
            await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id="vci-r1",
                org_id="org-1",
                text="hello",
                voice_id="v1",
            )

        assert orchestrator.get_session_provider("vci-r1") == "elevenlabs"

    @pytest.mark.asyncio
    async def test_recovery_counter_resets_on_slow_response(self):
        settings = _make_settings(TTS_RECOVERY_COOLDOWN_SEC=0)
        primary = _mock_provider("elevenlabs", latency_ms=100)
        fallback = _mock_provider("cartesia", latency_ms=80)
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )
        session = _mock_session()

        orchestrator._session_state["vci-r2"] = SessionTTSState(
            active_provider="cartesia",
            last_switch_at=0,
        )

        for i in range(3):
            await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id="vci-r2",
                org_id="org-1",
                text="hello",
                voice_id="v1",
            )

        state = orchestrator._session_state["vci-r2"]
        assert state.recovery_healthy_count == 3

        slow_fallback = _mock_provider("cartesia", latency_ms=400)
        orchestrator._providers["cartesia"] = slow_fallback
        await orchestrator.synthesize_for_call(
            session,
            call_id=1,
            vapi_call_id="vci-r2",
            org_id="org-1",
            text="hello",
            voice_id="v1",
        )

        assert state.recovery_healthy_count == 0

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

        orchestrator._session_state["vci-r3"] = SessionTTSState(
            active_provider="cartesia",
            last_switch_at=0,
        )

        for i in range(7):
            await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id="vci-r3",
                org_id="org-1",
                text="hello",
                voice_id="v1",
            )

        assert orchestrator.get_session_provider("vci-r3") == "cartesia"


class TestOrchestratorSessionManagement:
    """
    [2.3-UNIT-002_P0] Given session state management,
    when sessions are managed, then state is isolated per vapi_call_id.
    """

    @pytest.mark.asyncio
    async def test_session_starts_with_primary_provider(self):
        settings = _make_settings()
        primary = _mock_provider("elevenlabs", latency_ms=100)
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary},
            app_settings=settings,
        )

        assert orchestrator.get_session_provider("new-vci") == "elevenlabs"

    @pytest.mark.asyncio
    async def test_reset_session_removes_state(self):
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
            vapi_call_id="vci-reset",
            org_id="org-1",
            text="hello",
            voice_id="v1",
        )

        assert "vci-reset" in orchestrator._session_state
        orchestrator.reset_session("vci-reset")
        assert "vci-reset" not in orchestrator._session_state

    @pytest.mark.asyncio
    async def test_latency_history_tracked_per_session(self):
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
            vapi_call_id="vci-hist",
            org_id="org-1",
            text="hello",
            voice_id="v1",
        )
        await orchestrator.synthesize_for_call(
            session,
            call_id=1,
            vapi_call_id="vci-hist",
            org_id="org-1",
            text="hello",
            voice_id="v1",
        )

        history = orchestrator.get_session_latency_history("vci-hist")
        assert len(history) == 2


class TestOrchestratorAllProvidersFailed:
    """
    [2.3-UNIT-002_P0] Given both providers fail, when synthesize is called,
    then TTSAllProvidersFailedError is raised.
    """

    @pytest.mark.asyncio
    async def test_both_providers_fail_raises_error(self):
        settings = _make_settings()
        primary = _mock_provider("elevenlabs", error=True, error_message="Timeout")
        fallback = _mock_provider("cartesia", error=True, error_message="Timeout")
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )
        session = _mock_session()

        with pytest.raises(TTSAllProvidersFailedError):
            await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id="vci-fail",
                org_id="org-1",
                text="hello",
                voice_id="v1",
            )

    @pytest.mark.asyncio
    async def test_session_stays_on_last_attempted_provider_after_failure(self):
        settings = _make_settings()
        primary = _mock_provider("elevenlabs", error=True, error_message="Timeout")
        fallback = _mock_provider("cartesia", error=True, error_message="Timeout")
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )
        session = _mock_session()

        with pytest.raises(TTSAllProvidersFailedError):
            await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id="vci-fail2",
                org_id="org-1",
                text="hello",
                voice_id="v1",
            )

        assert orchestrator.get_session_provider("vci-fail2") == "cartesia"

    @pytest.mark.asyncio
    async def test_all_failed_emits_voice_event(self):
        settings = _make_settings()
        primary = _mock_provider("elevenlabs", error=True, error_message="Timeout")
        fallback = _mock_provider("cartesia", error=True, error_message="Timeout")
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )
        session = _mock_session()

        with pytest.raises(TTSAllProvidersFailedError):
            await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id="vci-fail3",
                org_id="org-1",
                text="hello",
                voice_id="v1",
            )

        calls = session.execute.call_args_list
        voice_event_calls = [
            c for c in calls if len(c[0]) > 0 and "voice_events" in str(c[0][0])
        ]
        assert len(voice_event_calls) >= 1

    @pytest.mark.asyncio
    async def test_primary_error_falls_back_to_secondary(self):
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
            vapi_call_id="vci-fb",
            org_id="org-1",
            text="hello",
            voice_id="v1",
        )

        assert response.provider == "cartesia"
        assert response.error is False
        assert orchestrator.get_session_provider("vci-fb") == "cartesia"
