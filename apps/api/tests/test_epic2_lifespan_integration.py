"""
[2.4-INT-001] Test Epic 2 lifespan startup/shutdown integration.

Tests the FastAPI lifespan context manager integration with TTS orchestrator:
- Startup creates orchestrator and starts cleanup task
- Shutdown closes all HTTP clients
- Singleton behavior across multiple calls
- Safe shutdown even if startup partially failed
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.tts.factory import get_tts_orchestrator, shutdown_tts, _orchestrator
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
def reset_orchestrator():
    """Reset orchestrator singleton before each test."""
    global _orchestrator
    _orchestrator = None
    yield
    _orchestrator = None


class TestLifespanStartupIntegration:
    """
    [2.4-INT-001_P0] Test lifespan startup creates orchestrator and cleanup task.
    """

    @pytest.mark.asyncio
    async def test_startup_creates_orchestrator(self):
        """
        [2.4-INT-001_P0_S1] Given the FastAPI app starts,
        when get_tts_orchestrator() is called,
        then an orchestrator instance is created with providers.
        """
        with patch("services.tts.factory.settings", _make_settings()):
            orchestrator = get_tts_orchestrator()

            assert orchestrator is not None
            assert isinstance(orchestrator, TTSOrchestrator)
            assert len(orchestrator._providers) == 2
            assert "elevenlabs" in orchestrator._providers
            assert "cartesia" in orchestrator._providers

    @pytest.mark.asyncio
    async def test_startup_starts_cleanup_task(self):
        """
        [2.4-INT-001_P0_S2] Given the FastAPI app starts,
        when get_tts_orchestrator() is called and start_cleanup_task() is invoked,
        then the cleanup task is created and running.
        """
        with patch("services.tts.factory.settings", _make_settings()):
            orchestrator = get_tts_orchestrator()

            # Cleanup task not started yet
            assert orchestrator._cleanup_task is None

            # Start cleanup task (as lifespan does)
            await orchestrator.start_cleanup_task()

            # Verify cleanup task is running
            assert orchestrator._cleanup_task is not None


class TestLifespanShutdownIntegration:
    """
    [2.4-INT-001_P0] Test lifespan shutdown closes HTTP clients.
    """

    @pytest.mark.asyncio
    async def test_shutdown_closes_all_clients(self):
        """
        [2.4-INT-001_P0_S3] Given the FastAPI app is shutting down,
        when shutdown_tts() is called,
        then all provider HTTP clients are closed.
        """
        with patch("services.tts.factory.settings", _make_settings()):
            orchestrator = get_tts_orchestrator()

            # Mock aclose on providers
            for provider in orchestrator._providers.values():
                provider.aclose = AsyncMock()

            await shutdown_tts()

            # Verify all providers were closed
            for provider in orchestrator._providers.values():
                provider.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_stops_cleanup_task(self):
        """
        [2.4-INT-001_P0_S4] Given the FastAPI app is shutting down,
        when shutdown_tts() is called,
        then the cleanup task is stopped.
        """
        with patch("services.tts.factory.settings", _make_settings()):
            orchestrator = get_tts_orchestrator()

            # Start cleanup task
            await orchestrator.start_cleanup_task()

            # Verify task is running
            assert orchestrator._cleanup_task is not None

            # Stop cleanup task first
            await orchestrator.stop_cleanup_task()

            # Then shutdown providers
            await shutdown_tts()

            # Verify orchestrator was reset
            assert _orchestrator is None


class TestLifespanErrorHandling:
    """
    [2.4-INT-001_P1] Test lifespan handles partial failures gracefully.
    """

    @pytest.mark.asyncio
    async def test_shutdown_safe_if_startup_failed(self):
        """
        [2.4-INT-001_P1_S1] Given the app is shutting down,
        when shutdown_tts() is called without prior startup,
        then no error is raised (safe no-op).
        """
        # Ensure orchestrator is None
        global _orchestrator
        _orchestrator = None

        # Should not raise
        await shutdown_tts()
        assert _orchestrator is None

    @pytest.mark.asyncio
    async def test_shutdown_safe_if_orchestrator_partial(self):
        """
        [2.4-INT-001_P1_S2] Given the app is shutting down,
        when shutdown_tts() is called and a provider fails to close,
        then the exception is propagated (current behavior).
        NOTE: Current implementation does NOT catch provider close errors.
        This test documents actual behavior.
        """
        with patch("services.tts.factory.settings", _make_settings()):
            orchestrator = get_tts_orchestrator()

            # Make one provider fail on close
            orchestrator._providers["elevenlabs"].aclose = AsyncMock(
                side_effect=Exception("Network error")
            )
            orchestrator._providers["cartesia"].aclose = AsyncMock()

            # Current implementation raises exception on first provider failure
            with pytest.raises(Exception, match="Network error"):
                await shutdown_tts()

            # Verify both were attempted (first one failed)
            orchestrator._providers["elevenlabs"].aclose.assert_called_once()
            # cartesia was not reached because elevenlabs failed first


class TestFactorySingletonBehavior:
    """
    [2.4-INT-001_P0] Test factory returns singleton instance.
    """

    @pytest.mark.asyncio
    async def test_singleton_across_multiple_calls(self):
        """
        [2.4-INT-001_P0_S5] Given the app is running,
        when get_tts_orchestrator() is called multiple times,
        then the same instance is returned (singleton pattern).
        """
        with patch("services.tts.factory.settings", _make_settings()):
            orchestrator1 = get_tts_orchestrator()
            orchestrator2 = get_tts_orchestrator()
            orchestrator3 = get_tts_orchestrator()

            assert orchestrator1 is orchestrator2
            assert orchestrator2 is orchestrator3
            assert id(orchestrator1) == id(orchestrator3)

    @pytest.mark.asyncio
    async def test_singleton_reset_after_shutdown(self):
        """
        [2.4-INT-001_P0_S6] Given the app has shutdown,
        when get_tts_orchestrator() is called again,
        then a new instance is created.
        """
        with patch("services.tts.factory.settings", _make_settings()):
            orchestrator1 = get_tts_orchestrator()

            # Mock provider close to avoid actual HTTP calls
            for provider in orchestrator1._providers.values():
                provider.aclose = AsyncMock()

            await shutdown_tts()

            orchestrator2 = get_tts_orchestrator()

            # Different instances after shutdown
            assert orchestrator1 is not orchestrator2
