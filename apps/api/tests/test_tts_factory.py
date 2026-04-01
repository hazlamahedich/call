"""
[2.3-UNIT-012] Test TTS factory — provider selection, singleton caching, shutdown lifecycle.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.tts.base import TTSProviderBase
from services.tts.orchestrator import TTSOrchestrator

import services.tts.factory as factory_module


def _make_settings(elevenlabs_key="test-key", cartesia_key="test-key"):
    s = MagicMock()
    s.ELEVENLABS_API_KEY = elevenlabs_key
    s.CARTESIA_API_KEY = cartesia_key
    s.TTS_PRIMARY_PROVIDER = "elevenlabs"
    s.TTS_FALLBACK_PROVIDER = "cartesia"
    s.TTS_LATENCY_THRESHOLD_MS = 500
    s.TTS_CONSECUTIVE_SLOW_THRESHOLD = 3
    s.TTS_AUTO_RECOVERY_ENABLED = True
    s.TTS_RECOVERY_HEALTHY_COUNT = 5
    s.TTS_RECOVERY_LATENCY_MS = 300
    s.TTS_RECOVERY_COOLDOWN_SEC = 60
    s.TTS_SESSION_TTL_SEC = 7200
    return s


@pytest.fixture(autouse=True)
def _reset_factory():
    factory_module._orchestrator = None
    yield
    factory_module._orchestrator = None


class TestGetTTSOrchestrator:
    """
    [2.3-UNIT-012_P0] Given factory function, when called,
    then it creates orchestrator with correct providers.
    """

    @pytest.mark.asyncio
    async def test_P0_creates_orchestrator_with_both_keys(self):
        mock_settings = _make_settings(elevenlabs_key="key-el", cartesia_key="key-ca")

        with patch("services.tts.factory.settings", mock_settings):
            with (
                patch("services.tts.factory.ElevenLabsProvider") as mock_el,
                patch("services.tts.factory.CartesiaProvider") as mock_ca,
            ):
                mock_el_instance = MagicMock()
                mock_el.return_value = mock_el_instance
                mock_ca_instance = MagicMock()
                mock_ca.return_value = mock_ca_instance

                orch = factory_module.get_tts_orchestrator()

                assert isinstance(orch, TTSOrchestrator)
                assert "elevenlabs" in orch._providers
                assert "cartesia" in orch._providers

    @pytest.mark.asyncio
    async def test_P0_returns_cached_orchestrator_on_second_call(self):
        with patch("services.tts.factory.settings", _make_settings()):
            with (
                patch("services.tts.factory.ElevenLabsProvider"),
                patch("services.tts.factory.CartesiaProvider"),
            ):
                orch1 = factory_module.get_tts_orchestrator()
                orch2 = factory_module.get_tts_orchestrator()

                assert orch1 is orch2

    @pytest.mark.asyncio
    async def test_P0_creates_only_elevenlabs_when_cartesia_missing(self):
        with patch(
            "services.tts.factory.settings",
            _make_settings(cartesia_key=""),
        ):
            with patch("services.tts.factory.ElevenLabsProvider") as mock_el:
                mock_el.return_value = MagicMock()
                orch = factory_module.get_tts_orchestrator()

                assert "elevenlabs" in orch._providers
                assert "cartesia" not in orch._providers

    @pytest.mark.asyncio
    async def test_P0_creates_only_cartesia_when_elevenlabs_missing(self):
        with patch(
            "services.tts.factory.settings",
            _make_settings(elevenlabs_key=""),
        ):
            with patch("services.tts.factory.CartesiaProvider") as mock_ca:
                mock_ca.return_value = MagicMock()
                orch = factory_module.get_tts_orchestrator()

                assert "cartesia" in orch._providers
                assert "elevenlabs" not in orch._providers

    @pytest.mark.asyncio
    async def test_P0_creates_empty_orchestrator_when_no_keys(self):
        with patch(
            "services.tts.factory.settings",
            _make_settings(elevenlabs_key="", cartesia_key=""),
        ):
            orch = factory_module.get_tts_orchestrator()

            assert isinstance(orch, TTSOrchestrator)
            assert len(orch._providers) == 0


class TestShutdownTTS:
    """
    [2.3-UNIT-012_P0] Given shutdown function, when called,
    then it stops cleanup task, closes providers, resets global.
    """

    @pytest.mark.asyncio
    async def test_P0_shutdown_with_active_orchestrator(self):
        mock_orch = MagicMock(spec=TTSOrchestrator)
        mock_orch.stop_cleanup_task = AsyncMock()
        mock_provider_1 = MagicMock(spec=TTSProviderBase)
        mock_provider_1.aclose = AsyncMock()
        mock_provider_2 = MagicMock(spec=TTSProviderBase)
        mock_provider_2.aclose = AsyncMock()
        mock_orch._providers = {
            "elevenlabs": mock_provider_1,
            "cartesia": mock_provider_2,
        }

        factory_module._orchestrator = mock_orch

        await factory_module.shutdown_tts()

        mock_orch.stop_cleanup_task.assert_called_once()
        mock_provider_1.aclose.assert_called_once()
        mock_provider_2.aclose.assert_called_once()
        assert factory_module._orchestrator is None

    @pytest.mark.asyncio
    async def test_P0_shutdown_when_none_is_noop(self):
        factory_module._orchestrator = None

        await factory_module.shutdown_tts()

        assert factory_module._orchestrator is None
