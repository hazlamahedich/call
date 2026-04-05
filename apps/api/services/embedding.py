from services.embedding.service import EmbeddingService, MAX_BATCH_SIZE
from services.embedding.providers import create_embedding_provider
from services.embedding.providers.base import EmbeddingProvider

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536

__all__ = [
    "EmbeddingService",
    "MAX_BATCH_SIZE",
    "EMBEDDING_MODEL",
    "EMBEDDING_DIMENSIONS",
    "create_embedding_provider",
    "EmbeddingProvider",
]
