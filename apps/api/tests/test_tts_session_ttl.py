"""
[2.3-UNIT-008] Test TTS session TTL cleanup.
"""

import time
import pytest
from unittest.mock import MagicMock

from services.tts.orchestrator import TTSOrchestrator, SessionTTSState


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
        "TTS_SESSION_TTL_SEC": 100,
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        setattr(s, k, v)
    return s


class TestSessionTTL:
    """
    [2.3-UNIT-008_P0] Given stale session entries older than TTL,
    when _cleanup_stale_sessions runs, then old entries are removed.
    """

    def test_removes_stale_sessions(self):
        settings = _make_settings(TTS_SESSION_TTL_SEC=100)
        orchestrator = TTSOrchestrator(
            providers={},
            app_settings=settings,
        )

        old_time = time.monotonic() - 200
        orchestrator._session_state["stale-1"] = SessionTTSState(
            active_provider="elevenlabs",
            created_at=old_time,
        )
        orchestrator._session_state["stale-2"] = SessionTTSState(
            active_provider="cartesia",
            created_at=old_time,
        )
        orchestrator._session_state["fresh-1"] = SessionTTSState(
            active_provider="elevenlabs",
        )

        cleaned = orchestrator._cleanup_stale_sessions()

        assert cleaned == 2
        assert "stale-1" not in orchestrator._session_state
        assert "stale-2" not in orchestrator._session_state
        assert "fresh-1" in orchestrator._session_state

    def test_does_not_remove_active_sessions(self):
        settings = _make_settings(TTS_SESSION_TTL_SEC=7200)
        orchestrator = TTSOrchestrator(
            providers={},
            app_settings=settings,
        )

        orchestrator._session_state["active-1"] = SessionTTSState(
            active_provider="elevenlabs",
        )
        orchestrator._session_state["active-2"] = SessionTTSState(
            active_provider="cartesia",
        )

        cleaned = orchestrator._cleanup_stale_sessions()

        assert cleaned == 0
        assert "active-1" in orchestrator._session_state
        assert "active-2" in orchestrator._session_state


class TestCleanupTaskInterval:
    """
    [2.3-UNIT-008_P1] Background cleanup runs at TTL/2 interval.
    """

    @pytest.mark.asyncio
    async def test_start_and_stop_cleanup_task(self):
        settings = _make_settings(TTS_SESSION_TTL_SEC=100)
        orchestrator = TTSOrchestrator(
            providers={},
            app_settings=settings,
        )

        await orchestrator.start_cleanup_task()
        assert orchestrator._cleanup_task is not None

        await orchestrator.stop_cleanup_task()
        assert orchestrator._cleanup_task is None

    @pytest.mark.asyncio
    async def test_start_idempotent(self):
        settings = _make_settings()
        orchestrator = TTSOrchestrator(
            providers={},
            app_settings=settings,
        )

        await orchestrator.start_cleanup_task()
        task1 = orchestrator._cleanup_task
        await orchestrator.start_cleanup_task()
        task2 = orchestrator._cleanup_task

        assert task1 is task2

        await orchestrator.stop_cleanup_task()
