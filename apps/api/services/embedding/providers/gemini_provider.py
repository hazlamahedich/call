import logging
from typing import List

from google import genai
from google.genai import types

from .base import EmbeddingProvider

logger = logging.getLogger(__name__)


class GeminiEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self, api_key: str, model: str = "gemini-embedding-001", dimensions: int = 3072
    ):
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._dimensions = dimensions

    async def embed(
        self, text: str, *, task_type: str = "RETRIEVAL_DOCUMENT"
    ) -> List[float]:
        result = await self._client.aio.models.embed_content(
            model=self._model,
            contents=text,
            config=types.EmbedContentConfig(
                output_dimensionality=self._dimensions,
                task_type=task_type,
            ),
        )
        return result.embeddings[0].values

    async def embed_batch(
        self, texts: List[str], *, task_type: str = "RETRIEVAL_DOCUMENT"
    ) -> List[List[float]]:
        result = await self._client.aio.models.embed_content(
            model=self._model,
            contents=texts,
            config=types.EmbedContentConfig(
                output_dimensionality=self._dimensions,
                task_type=task_type,
            ),
        )
        return [e.values for e in result.embeddings]

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions
