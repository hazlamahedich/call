from config.settings import Settings
from .base import LLMProvider
from .openai_provider import OpenAILLMProvider
from .gemini_provider import GeminiLLMProvider


def create_llm_provider(settings: Settings) -> LLMProvider:
    if settings.AI_PROVIDER == "gemini":
        return GeminiLLMProvider(
            api_key=settings.GEMINI_API_KEY,
            model=settings.AI_LLM_MODEL,
        )
    return OpenAILLMProvider(
        api_key=settings.OPENAI_API_KEY,
        model=settings.AI_LLM_MODEL,
    )
