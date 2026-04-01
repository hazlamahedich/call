"""
[2.3-UNIT-013] Test TTS orchestrator session accessor edge cases — latency history,
reset idempotency, fallback/recovery conditions, cleanup task.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from services.tts.base import TTSProviderBase, TTSResponse
from services.tts.orchestrator import TTSOrchestrator


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


class TestGetSessionEdgeCases:
    """
    [2.3-UNIT-013_P2] Edge cases for session accessor methods.
    """

    def test_P2_latency_history_returns_empty_for_unknown_session(self):
        settings = _make_settings()
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": _mock_provider("elevenlabs")},
            app_settings=settings,
        )

        result = orchestrator.get_session_latency_history("nonexistent-vci")
        assert result == []

    def test_P2_reset_session_idempotent_for_nonexistent_key(self):
        settings = _make_settings()
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": _mock_provider("elevenlabs")},
            app_settings=settings,
        )

        orchestrator.reset_session("nonexistent-vci")
        assert "nonexistent-vci" not in orchestrator._session_state

    def test_P2_check_fallback_condition_returns_false_for_missing_state(self):
        settings = _make_settings()
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": _mock_provider("elevenlabs")},
            app_settings=settings,
        )

        assert orchestrator._check_fallback_condition("nonexistent") is False

    def test_P2_check_recovery_condition_returns_false_for_missing_state(self):
        settings = _make_settings()
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": _mock_provider("elevenlabs")},
            app_settings=settings,
        )

        assert orchestrator._check_recovery_condition("nonexistent") is False


class TestGetOrCreateSessionFallback:
    """
    [2.3-UNIT-013_P1] _get_or_create_session falls back when primary not in providers.
    """

    def test_P1_falls_back_to_first_available_when_primary_missing(self):
        settings = _make_settings(TTS_PRIMARY_PROVIDER="nonexistent")
        provider = _mock_provider("cartesia")
        orchestrator = TTSOrchestrator(
            providers={"cartesia": provider},
            app_settings=settings,
        )

        state = orchestrator._get_or_create_session("vci-new")

        assert state.active_provider == "cartesia"


class TestStopCleanupTaskNone:
    """
    [2.3-UNIT-013_P2] stop_cleanup_task handles None task.
    """

    @pytest.mark.asyncio
    async def test_P2_stop_cleanup_task_when_none_is_noop(self):
        settings = _make_settings()
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": _mock_provider("elevenlabs")},
            app_settings=settings,
        )

        assert orchestrator._cleanup_task is None
        await orchestrator.stop_cleanup_task()
        assert orchestrator._cleanup_task is None
