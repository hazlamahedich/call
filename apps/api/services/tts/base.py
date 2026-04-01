from __future__ import annotations

import abc
from dataclasses import dataclass


@dataclass
class TTSResponse:
    audio_bytes: bytes
    latency_ms: float
    provider: str
    content_type: str
    error: bool = False
    error_message: str | None = None


class TTSProviderBase(abc.ABC):
    @abc.abstractmethod
    async def synthesize(
        self, text: str, voice_id: str, model: str | None = None
    ) -> TTSResponse: ...

    @abc.abstractmethod
    async def health_check(self) -> bool: ...

    @property
    @abc.abstractmethod
    def provider_name(self) -> str: ...

    async def aclose(self) -> None:
        pass
