from abc import ABC, abstractmethod
from typing import List


class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed(
        self, text: str, *, task_type: str = "RETRIEVAL_DOCUMENT"
    ) -> List[float]: ...

    @abstractmethod
    async def embed_batch(
        self, texts: List[str], *, task_type: str = "RETRIEVAL_DOCUMENT"
    ) -> List[List[float]]: ...

    @property
    @abstractmethod
    def model_name(self) -> str: ...

    @property
    @abstractmethod
    def dimensions(self) -> int: ...
