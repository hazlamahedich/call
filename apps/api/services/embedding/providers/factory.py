from config.settings import Settings
from .base import EmbeddingProvider
from .openai_provider import OpenAIEmbeddingProvider
from .gemini_provider import GeminiEmbeddingProvider


def create_embedding_provider(settings: Settings) -> EmbeddingProvider:
    if settings.AI_PROVIDER == "gemini":
        return GeminiEmbeddingProvider(
            api_key=settings.GEMINI_API_KEY,
            model=settings.AI_EMBEDDING_MODEL,
            dimensions=settings.AI_EMBEDDING_DIMENSIONS,
        )
    return OpenAIEmbeddingProvider(
        api_key=settings.OPENAI_API_KEY,
        model=settings.AI_EMBEDDING_MODEL,
        dimensions=settings.AI_EMBEDDING_DIMENSIONS,
    )
