from __future__ import annotations

import logging

from config.settings import settings
from .base import TTSProviderBase
from .elevenlabs import ElevenLabsProvider
from .cartesia import CartesiaProvider
from .orchestrator import TTSOrchestrator

logger = logging.getLogger(__name__)

_orchestrator: TTSOrchestrator | None = None


def get_tts_orchestrator() -> TTSOrchestrator:
    global _orchestrator
    if _orchestrator is not None:
        return _orchestrator

    providers: dict[str, TTSProviderBase] = {}

    if settings.ELEVENLABS_API_KEY:
        providers["elevenlabs"] = ElevenLabsProvider()
    else:
        logger.warning(
            "ElevenLabs API key not configured",
            extra={"code": "TTS_CONFIG_INVALID"},
        )

    if settings.CARTESIA_API_KEY:
        providers["cartesia"] = CartesiaProvider()
    else:
        logger.warning(
            "Cartesia API key not configured",
            extra={"code": "TTS_CONFIG_INVALID"},
        )

    if not providers:
        logger.warning(
            "No TTS providers configured",
            extra={"code": "TTS_NO_PROVIDERS"},
        )

    _orchestrator = TTSOrchestrator(providers=providers, app_settings=settings)
    return _orchestrator


async def shutdown_tts() -> None:
    global _orchestrator
    if _orchestrator is None:
        return
    await _orchestrator.stop_cleanup_task()
    for provider in _orchestrator._providers.values():
        await provider.aclose()
    _orchestrator = None
