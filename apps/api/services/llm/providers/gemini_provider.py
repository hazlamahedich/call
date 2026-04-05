import logging
from typing import AsyncIterator, List

from google import genai
from google.genai import types

from .base import LLMMessage, LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class GeminiLLMProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def _map_messages(self, messages: List[LLMMessage]) -> list:
        contents = []
        for m in messages:
            role = "user" if m.role in ("user", "system") else "model"
            contents.append({"role": role, "parts": [{"text": m.content}]})
        return contents

    async def complete(
        self,
        messages: List[LLMMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> LLMResponse:
        contents = self._map_messages(messages)
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        result = await self._client.aio.models.generate_content(
            model=self._model,
            contents=contents,
            config=config,
        )
        usage = {}
        if result.usage_metadata:
            usage = {
                "prompt_tokens": getattr(result.usage_metadata, "prompt_token_count", 0)
                or 0,
                "completion_tokens": getattr(
                    result.usage_metadata, "candidates_token_count", 0
                )
                or 0,
            }
        return LLMResponse(content=result.text or "", model=self._model, usage=usage)

    async def stream(
        self,
        messages: List[LLMMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> AsyncIterator[str]:
        contents = self._map_messages(messages)
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=contents,
            config=config,
        )
        async for chunk in response:
            if chunk.text:
                yield chunk.text

    @property
    def model_name(self) -> str:
        return self._model
