import logging
from typing import List

from openai import AsyncOpenAI

from .base import EmbeddingProvider

logger = logging.getLogger(__name__)


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        dimensions: int = 1536,
    ):
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._dimensions = dimensions

    async def embed(
        self, text: str, *, task_type: str = "RETRIEVAL_DOCUMENT"
    ) -> List[float]:
        response = await self._client.embeddings.create(model=self._model, input=text)
        return response.data[0].embedding

    async def embed_batch(
        self, texts: List[str], *, task_type: str = "RETRIEVAL_DOCUMENT"
    ) -> List[List[float]]:
        response = await self._client.embeddings.create(model=self._model, input=texts)
        return [item.embedding for item in response.data]

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions
