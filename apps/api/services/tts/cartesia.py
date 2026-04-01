from __future__ import annotations

import logging
import time

import httpx

from config.settings import settings
from .base import TTSProviderBase, TTSResponse

logger = logging.getLogger(__name__)


class CartesiaProvider(TTSProviderBase):
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=2.0, read=3.0, write=2.0, pool=2.0),
        )

    @property
    def provider_name(self) -> str:
        return "cartesia"

    async def synthesize(
        self, text: str, voice_id: str, model: str | None = None
    ) -> TTSResponse:
        url = f"{settings.CARTESIA_BASE_URL}/tts/bytes"
        headers = {
            "X-API-Key": settings.CARTESIA_API_KEY,
            "Content-Type": "application/json",
        }
        body = {
            "model_id": model or "sonic-english",
            "transcript": text,
            "voice": {"mode": "id", "id": voice_id},
            "output_format": {"container": "mp3", "bit_rate": 128000},
        }
        start = time.monotonic()
        try:
            resp = await self._client.post(url, json=body, headers=headers)
            elapsed = (time.monotonic() - start) * 1000
            if resp.status_code == 401 or resp.status_code == 403:
                logger.error(
                    "Cartesia API auth error",
                    extra={
                        "code": "TTS_PROVIDER_UNAVAILABLE",
                        "provider": "cartesia",
                        "status": resp.status_code,
                    },
                )
                return TTSResponse(
                    audio_bytes=b"",
                    latency_ms=elapsed,
                    provider="cartesia",
                    content_type="",
                    error=True,
                    error_message=f"Auth error: {resp.status_code}",
                )
            if resp.status_code == 429:
                logger.warning(
                    "Cartesia rate limit hit",
                    extra={
                        "code": "TTS_PROVIDER_UNAVAILABLE",
                        "provider": "cartesia",
                        "status": 429,
                    },
                )
                return TTSResponse(
                    audio_bytes=b"",
                    latency_ms=elapsed,
                    provider="cartesia",
                    content_type="",
                    error=True,
                    error_message="Rate limited",
                )
            resp.raise_for_status()
            return TTSResponse(
                audio_bytes=resp.content,
                latency_ms=elapsed,
                provider="cartesia",
                content_type=resp.headers.get("content-type", "audio/mpeg"),
            )
        except httpx.TimeoutException:
            elapsed = (time.monotonic() - start) * 1000
            logger.warning(
                "Cartesia TTS timeout",
                extra={
                    "code": "TTS_PROVIDER_UNAVAILABLE",
                    "provider": "cartesia",
                    "latency_ms": round(elapsed, 2),
                },
            )
            return TTSResponse(
                audio_bytes=b"",
                latency_ms=elapsed,
                provider="cartesia",
                content_type="",
                error=True,
                error_message="Timeout",
            )
        except Exception as exc:
            elapsed = (time.monotonic() - start) * 1000
            logger.error(
                "Cartesia TTS error",
                extra={
                    "code": "TTS_PROVIDER_UNAVAILABLE",
                    "provider": "cartesia",
                    "error": str(exc),
                },
            )
            return TTSResponse(
                audio_bytes=b"",
                latency_ms=elapsed,
                provider="cartesia",
                content_type="",
                error=True,
                error_message=str(exc),
            )

    async def health_check(self) -> bool:
        return bool(settings.CARTESIA_API_KEY)

    async def aclose(self) -> None:
        await self._client.aclose()
