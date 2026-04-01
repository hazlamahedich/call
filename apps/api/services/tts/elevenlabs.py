from __future__ import annotations

import logging
import time

import httpx

from config.settings import settings
from .base import TTSProviderBase, TTSResponse

logger = logging.getLogger(__name__)


class ElevenLabsProvider(TTSProviderBase):
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=1.0, read=1.0, write=2.0, pool=2.0),
        )

    @property
    def provider_name(self) -> str:
        return "elevenlabs"

    async def synthesize(
        self, text: str, voice_id: str, model: str | None = None
    ) -> TTSResponse:
        url = f"{settings.ELEVENLABS_BASE_URL}/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": settings.ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
        }
        body = {
            "text": text,
            "model_id": model or "eleven_multilingual_v2",
            "output_format": "mp3_44100_128",
        }
        start = time.monotonic()
        try:
            resp = await self._client.post(url, json=body, headers=headers)
            elapsed = (time.monotonic() - start) * 1000
            if resp.status_code == 401 or resp.status_code == 403:
                logger.error(
                    "ElevenLabs API auth error",
                    extra={
                        "code": "TTS_PROVIDER_UNAVAILABLE",
                        "provider": "elevenlabs",
                        "status": resp.status_code,
                    },
                )
                return TTSResponse(
                    audio_bytes=b"",
                    latency_ms=elapsed,
                    provider="elevenlabs",
                    content_type="",
                    error=True,
                    error_message=f"Auth error: {resp.status_code}",
                )
            if resp.status_code == 429:
                logger.warning(
                    "ElevenLabs rate limit hit",
                    extra={
                        "code": "TTS_PROVIDER_UNAVAILABLE",
                        "provider": "elevenlabs",
                        "status": 429,
                    },
                )
                return TTSResponse(
                    audio_bytes=b"",
                    latency_ms=elapsed,
                    provider="elevenlabs",
                    content_type="",
                    error=True,
                    error_message="Rate limited",
                )
            resp.raise_for_status()
            return TTSResponse(
                audio_bytes=resp.content,
                latency_ms=elapsed,
                provider="elevenlabs",
                content_type=resp.headers.get("content-type", "audio/mpeg"),
            )
        except httpx.TimeoutException:
            elapsed = (time.monotonic() - start) * 1000
            logger.warning(
                "ElevenLabs TTS timeout",
                extra={
                    "code": "TTS_PROVIDER_UNAVAILABLE",
                    "provider": "elevenlabs",
                    "latency_ms": round(elapsed, 2),
                },
            )
            return TTSResponse(
                audio_bytes=b"",
                latency_ms=elapsed,
                provider="elevenlabs",
                content_type="",
                error=True,
                error_message="Timeout",
            )
        except Exception as exc:
            elapsed = (time.monotonic() - start) * 1000
            logger.error(
                "ElevenLabs TTS error",
                extra={
                    "code": "TTS_PROVIDER_UNAVAILABLE",
                    "provider": "elevenlabs",
                    "error": str(exc),
                },
            )
            return TTSResponse(
                audio_bytes=b"",
                latency_ms=elapsed,
                provider="elevenlabs",
                content_type="",
                error=True,
                error_message=str(exc),
            )

    async def health_check(self) -> bool:
        if not settings.ELEVENLABS_API_KEY:
            return False
        try:
            resp = await self._client.get(
                f"{settings.ELEVENLABS_BASE_URL}/user",
                headers={"xi-api-key": settings.ELEVENLABS_API_KEY},
            )
            return resp.status_code == 200
        except Exception:
            return False

    async def aclose(self) -> None:
        await self._client.aclose()
