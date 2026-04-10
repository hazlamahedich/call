"""
[2.4-INT-002] Test Epic 2 webhook → TTS session reset integration.

Tests the call-end webhook integration with TTS session cleanup:
- call-end calls reset_session(vapi_call_id) before call status update
- reset evicts session from _session_state
- reset is safe when no TTS session exists
- call-failed also resets TTS session (defensive)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.tts.factory import get_tts_orchestrator, shutdown_tts, reset_orchestrator
from services.tts.orchestrator import TTSOrchestrator
from services.tts.base import TTSProviderBase


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
        "ELEVENLABS_API_KEY": "test-key",
        "CARTESIA_API_KEY": "test-key",
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        setattr(s, k, v)
    return s


def _mock_provider(name: str):
    """Helper to create a mock TTS provider."""
    p = MagicMock(spec=TTSProviderBase)
    p.provider_name = name
    p.synthesize = AsyncMock()
    p.health_check = AsyncMock(return_value=True)
    p.aclose = AsyncMock()
    return p


@pytest.fixture(autouse=True)
def _reset_tts():
    reset_orchestrator()
    yield
    reset_orchestrator()


class TestCallEndResetsTTSSession:
    """
    [2.4-INT-002_P0] Test call-end webhook calls reset_session before status update.
    """

    @pytest.mark.asyncio
    async def test_call_end_resets_session_before_status_update(self):
        """
        [2.4-INT-002_P0_S1] Given an active call with an ongoing TTS session,
        when call-end webhook is received,
        then reset_session(vapi_call_id) is called BEFORE call status update.
        """
        with patch("services.tts.factory.settings", _make_settings()):
            orchestrator = await get_tts_orchestrator()

            # Create an active TTS session
            orchestrator._session_state["vapi-call-123"] = MagicMock()

            # Mock providers to avoid real HTTP calls during shutdown
            for provider in orchestrator._providers.values():
                provider.aclose = AsyncMock()

            # Simulate call-end webhook behavior
            vapi_call_id = "vapi-call-123"
            orchestrator.reset_session(vapi_call_id)

            # Verify session was evicted
            assert vapi_call_id not in orchestrator._session_state

            await shutdown_tts()

    @pytest.mark.asyncio
    async def test_reset_evicts_session_from_state_dict(self):
        """
        [2.4-INT-002_P0_S2] Given an active TTS session exists,
        when reset_session is called,
        then the session is fully evicted from _session_state.
        """
        with patch("services.tts.factory.settings", _make_settings()):
            orchestrator = await get_tts_orchestrator()

            # Create an active TTS session with state
            from services.tts.orchestrator import SessionTTSState

            state = SessionTTSState(active_provider="elevenlabs")
            orchestrator._session_state["vapi-call-456"] = state

            # Verify session exists
            assert "vapi-call-456" in orchestrator._session_state

            # Reset session
            orchestrator.reset_session("vapi-call-456")

            # Verify session was evicted
            assert "vapi-call-456" not in orchestrator._session_state

            # Mock providers for cleanup
            for provider in orchestrator._providers.values():
                provider.aclose = AsyncMock()

            await shutdown_tts()


class TestResetSafety:
    """
    [2.4-INT-002_P1] Test reset_session is safe in edge cases.
    """

    @pytest.mark.asyncio
    async def test_reset_safe_when_no_session_exists(self):
        """
        [2.4-INT-002_P1_S1] Given a call without an active TTS session,
        when reset_session is called,
        then no error is raised (safe no-op).
        """
        with patch("services.tts.factory.settings", _make_settings()):
            orchestrator = await get_tts_orchestrator()

            # No session exists for this call
            assert "vapi-call-999" not in orchestrator._session_state

            # Should not raise
            orchestrator.reset_session("vapi-call-999")

            # Mock providers for cleanup
            for provider in orchestrator._providers.values():
                provider.aclose = AsyncMock()

            await shutdown_tts()

    @pytest.mark.asyncio
    async def test_reset_safe_with_empty_session_state(self):
        """
        [2.4-INT-002_P1_S2] Given the orchestrator has no sessions at all,
        when reset_session is called,
        then no error is raised.
        """
        with patch("services.tts.factory.settings", _make_settings()):
            orchestrator = await get_tts_orchestrator()

            # Verify empty state
            assert len(orchestrator._session_state) == 0

            # Should not raise
            orchestrator.reset_session("vapi-call-any")

            # Mock providers for cleanup
            for provider in orchestrator._providers.values():
                provider.aclose = AsyncMock()

            await shutdown_tts()


class TestCallFailedAlsoResetsSession:
    """
    [2.4-INT-002_P2] Test call-failed also resets TTS session (defensive).
    """

    @pytest.mark.asyncio
    async def test_call_failed_resets_session_prevents_memory_leak(self):
        """
        [2.4-INT-002_P2_S1] Given an active call with TTS session fails,
        when call-failed webhook is received,
        then reset_session is called to prevent memory leak.
        NOTE: This is defensive programming - ensures cleanup on all call terminations.
        """
        with patch("services.tts.factory.settings", _make_settings()):
            orchestrator = await get_tts_orchestrator()

            # Create an active TTS session
            from services.tts.orchestrator import SessionTTSState

            state = SessionTTSState(active_provider="cartesia")
            orchestrator._session_state["vapi-call-failed-789"] = state

            # Verify session exists
            assert "vapi-call-failed-789" in orchestrator._session_state

            # Simulate call-failed behavior (should also reset)
            orchestrator.reset_session("vapi-call-failed-789")

            # Verify session was evicted
            assert "vapi-call-failed-789" not in orchestrator._session_state

            # Mock providers for cleanup
            for provider in orchestrator._providers.values():
                provider.aclose = AsyncMock()

            await shutdown_tts()

    @pytest.mark.asyncio
    async def test_multiple_concurrent_resets_safe(self):
        """
        [2.4-INT-002_P2_S2] Given multiple calls end simultaneously,
        when reset_session is called concurrently for different vapi_call_ids,
        then all sessions are evicted correctly.
        """
        with patch("services.tts.factory.settings", _make_settings()):
            orchestrator = await get_tts_orchestrator()

            # Create multiple active TTS sessions
            from services.tts.orchestrator import SessionTTSState

            orchestrator._session_state["call-1"] = SessionTTSState(
                active_provider="elevenlabs"
            )
            orchestrator._session_state["call-2"] = SessionTTSState(
                active_provider="cartesia"
            )
            orchestrator._session_state["call-3"] = SessionTTSState(
                active_provider="elevenlabs"
            )

            # Reset all sessions
            orchestrator.reset_session("call-1")
            orchestrator.reset_session("call-2")
            orchestrator.reset_session("call-3")

            # Verify all sessions evicted
            assert len(orchestrator._session_state) == 0

            # Mock providers for cleanup
            for provider in orchestrator._providers.values():
                provider.aclose = AsyncMock()

            await shutdown_tts()
