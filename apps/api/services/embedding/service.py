import hashlib
import logging
import random
from typing import List, Optional

from services.embedding.providers.base import EmbeddingProvider

logger = logging.getLogger(__name__)

MAX_BATCH_SIZE = 100
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 1.0
MAX_RETRY_DELAY = 30.0
CACHE_TTL = 7 * 24 * 60 * 60


class EmbeddingService:
    def __init__(self, provider: EmbeddingProvider, redis_client: Optional[any] = None):
        self.provider = provider
        self.redis_client = redis_client

    async def generate_embedding(
        self, text: str, *, task_type: str = "RETRIEVAL_DOCUMENT"
    ) -> List[float]:
        for attempt in range(MAX_RETRIES):
            try:
                embedding = await self.provider.embed(text, task_type=task_type)
                logger.debug(f"Generated embedding for {len(text)} chars")
                return embedding
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    import asyncio

                    delay = min(
                        INITIAL_RETRY_DELAY * (2**attempt) + random.uniform(0, 1),
                        MAX_RETRY_DELAY,
                    )
                    logger.warning(
                        f"Embedding attempt {attempt + 1} failed: {e}, retrying in {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Embedding failed after {MAX_RETRIES} attempts: {e}")
                    raise Exception(
                        f"Embedding failed after {MAX_RETRIES} attempts: {e}"
                    ) from e

    async def generate_embeddings_batch(
        self, texts: List[str], *, task_type: str = "RETRIEVAL_DOCUMENT"
    ) -> List[List[float]]:
        if len(texts) > MAX_BATCH_SIZE:
            raise ValueError(
                f"Batch size {len(texts)} exceeds maximum {MAX_BATCH_SIZE}"
            )

        for attempt in range(MAX_RETRIES):
            try:
                embeddings = await self.provider.embed_batch(texts, task_type=task_type)
                logger.info(f"Generated {len(embeddings)} embeddings")
                return embeddings
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    import asyncio

                    delay = min(
                        INITIAL_RETRY_DELAY * (2**attempt) + random.uniform(0, 1),
                        MAX_RETRY_DELAY,
                    )
                    logger.warning(
                        f"Batch embedding attempt {attempt + 1} failed: {e}, retrying in {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    raise Exception(
                        f"Batch embedding failed after {MAX_RETRIES} attempts: {e}"
                    ) from e

    async def get_cached_embedding(
        self, text_hash: str, org_id: str
    ) -> Optional[List[float]]:
        if not self.redis_client:
            return None
        cache_key = self._build_cache_key(text_hash, org_id)
        try:
            cached = await self.redis_client.get(cache_key)
            if cached:
                embedding = [float(x) for x in cached.decode("utf-8").split(",")]
                logger.debug(f"Cache hit for {cache_key}")
                return embedding
        except Exception as e:
            logger.warning(f"Redis cache lookup failed: {e}, continuing without cache")
        return None

    async def cache_embedding(
        self, text_hash: str, org_id: str, embedding: List[float]
    ) -> bool:
        if not self.redis_client:
            return False
        cache_key = self._build_cache_key(text_hash, org_id)
        try:
            embedding_str = ",".join(str(x) for x in embedding)
            await self.redis_client.setex(cache_key, CACHE_TTL, embedding_str)
            logger.debug(f"Cached embedding for {cache_key}")
            return True
        except Exception as e:
            logger.warning(f"Redis cache write failed: {e}, continuing without cache")
            return False

    def _build_cache_key(self, text_hash: str, org_id: str) -> str:
        return f"emb:v1:{self.provider.model_name}:{org_id}:{text_hash}"

    def compute_text_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    async def generate_with_cache(
        self, text: str, org_id: str, *, task_type: str = "RETRIEVAL_DOCUMENT"
    ) -> List[float]:
        text_hash = self.compute_text_hash(text)
        cached = await self.get_cached_embedding(text_hash, org_id)
        if cached:
            return cached
        embedding = await self.generate_embedding(text, task_type=task_type)
        await self.cache_embedding(text_hash, org_id, embedding)
        return embedding
