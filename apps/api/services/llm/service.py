import logging
from typing import AsyncIterator

from services.llm.providers.base import LLMMessage, LLMProvider, LLMResponse
from services.prompt_sanitizer import scrub_prompt

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self, provider: LLMProvider):
        self.provider = provider

    async def generate(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> str:
        messages = [
            LLMMessage(role="system", content=scrub_prompt(system)),
            LLMMessage(role="user", content=scrub_prompt(user)),
        ]
        response = await self.provider.complete(
            messages, temperature=temperature, max_tokens=max_tokens, **kwargs
        )
        return response.content

    async def generate_stream(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> AsyncIterator[str]:
        messages = [
            LLMMessage(role="system", content=scrub_prompt(system)),
            LLMMessage(role="user", content=scrub_prompt(user)),
        ]
        async for chunk in self.provider.stream(
            messages, temperature=temperature, max_tokens=max_tokens, **kwargs
        ):
            yield chunk

    async def summarize(self, text: str, max_length: int = 500) -> str:
        system = (
            f"You are a concise summarizer. Summarize the following text "
            f"in no more than {max_length} characters. Return only the summary."
        )
        return await self.generate(system, text, temperature=0.3, max_tokens=max_length)
