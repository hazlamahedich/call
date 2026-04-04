"""Embedding service for vector generation.

Generates OpenAI embeddings for text chunks with Redis caching.
"""

import hashlib
import logging
import random
from typing import List, Optional

import httpx
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# Configuration constants
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
MAX_BATCH_SIZE = 100
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 1.0
MAX_RETRY_DELAY = 30.0

# Cache configuration
CACHE_TTL = 7 * 24 * 60 * 60  # 7 days in seconds


class EmbeddingService:
    """Service for generating vector embeddings using OpenAI.

    Features:
    - Batch embedding for efficiency
    - Redis caching with fail-open
    - Retry logic for API failures
    """

    def __init__(self, api_key: str, redis_client: Optional[any] = None):
        """Initialize embedding service.

        Args:
            api_key: OpenAI API key
            redis_client: Optional Redis client for caching
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.redis_client = redis_client

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate vector embedding using text-embedding-3-small.

        Args:
            text: Text to embed

        Returns:
            1536-dimensional vector embedding

        Raises:
            Exception: If embedding generation fails after retries
        """
        for attempt in range(MAX_RETRIES):
            try:
                response = await self.client.embeddings.create(
                    model=EMBEDDING_MODEL, input=text
                )
                embedding = response.data[0].embedding
                logger.debug(f"Generated embedding for {len(text)} chars")
                return embedding

            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    delay = min(
                        INITIAL_RETRY_DELAY * (2**attempt) + random.uniform(0, 1),
                        MAX_RETRY_DELAY,
                    )
                    logger.warning(
                        f"Embedding attempt {attempt + 1} failed: {e}, "
                        f"retrying in {delay:.1f}s..."
                    )
                    import asyncio

                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Embedding failed after {MAX_RETRIES} attempts: {e}")
                    raise

    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts in one API call.

        Args:
            texts: List of texts to embed (max 100)

        Returns:
            List of vector embeddings

        Raises:
            ValueError: If batch size exceeds MAX_BATCH_SIZE
            Exception: If embedding generation fails after retries
        """
        if len(texts) > MAX_BATCH_SIZE:
            raise ValueError(
                f"Batch size {len(texts)} exceeds maximum {MAX_BATCH_SIZE}"
            )

        for attempt in range(MAX_RETRIES):
            try:
                response = await self.client.embeddings.create(
                    model=EMBEDDING_MODEL, input=texts
                )
                embeddings = [item.embedding for item in response.data]
                logger.info(f"Generated {len(embeddings)} embeddings")
                return embeddings

            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    delay = min(
                        INITIAL_RETRY_DELAY * (2**attempt) + random.uniform(0, 1),
                        MAX_RETRY_DELAY,
                    )
                    logger.warning(
                        f"Batch embedding attempt {attempt + 1} failed: {e}, "
                        f"retrying in {delay:.1f}s..."
                    )
                    import asyncio

                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Batch embedding failed after {MAX_RETRIES} attempts: {e}"
                    )
                    raise

    async def get_cached_embedding(
        self, text_hash: str, org_id: str
    ) -> Optional[List[float]]:
        """Check Redis cache for existing embedding.

        Args:
            text_hash: SHA-256 hash of text content
            org_id: Tenant organization ID

        Returns:
            Cached embedding if found, None otherwise

        Note:
            On Redis failure, logs warning and continues (fail-open).
        """
        if not self.redis_client:
            return None

        cache_key = self._build_cache_key(text_hash, org_id)

        try:
            cached = await self.redis_client.get(cache_key)
            if cached:
                # Parse cached embedding (stored as comma-separated string)
                embedding = [float(x) for x in cached.decode("utf-8").split(",")]
                logger.debug(f"Cache hit for {cache_key}")
                return embedding
        except Exception as e:
            # Fail-open on Redis error
            logger.warning(f"Redis cache lookup failed: {e}, continuing without cache")

        return None

    async def cache_embedding(
        self, text_hash: str, org_id: str, embedding: List[float]
    ) -> bool:
        """Cache embedding in Redis.

        Args:
            text_hash: SHA-256 hash of text content
            org_id: Tenant organization ID
            embedding: Embedding vector to cache

        Returns:
            True if cached successfully, False otherwise

        Note:
            On Redis failure, logs warning and continues (fail-open).
        """
        if not self.redis_client:
            return False

        cache_key = self._build_cache_key(text_hash, org_id)

        try:
            # Store embedding as comma-separated string
            embedding_str = ",".join(str(x) for x in embedding)
            await self.redis_client.setex(cache_key, CACHE_TTL, embedding_str)
            logger.debug(f"Cached embedding for {cache_key}")
            return True
        except Exception as e:
            # Fail-open on Redis error
            logger.warning(f"Redis cache write failed: {e}, continuing without cache")
            return False

    def _build_cache_key(self, text_hash: str, org_id: str) -> str:
        """Build Redis cache key for embedding.

        Args:
            text_hash: SHA-256 hash of text content
            org_id: Tenant organization ID

        Returns:
            Cache key string
        """
        # Format: emb:v1:{model}:{org_id}:{sha256_hash}
        return f"emb:v1:{EMBEDDING_MODEL}:{org_id}:{text_hash}"

    def compute_text_hash(self, text: str) -> str:
        """Compute SHA-256 hash of text for cache key.

        Args:
            text: Text content to hash

        Returns:
            Hexadecimal SHA-256 hash
        """
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    async def generate_with_cache(self, text: str, org_id: str) -> List[float]:
        """Generate embedding with Redis caching.

        Checks cache first, generates if not found, then caches result.

        Args:
            text: Text to embed
            org_id: Tenant organization ID

        Returns:
            1536-dimensional vector embedding
        """
        text_hash = self.compute_text_hash(text)

        # Check cache
        cached = await self.get_cached_embedding(text_hash, org_id)
        if cached:
            return cached

        # Generate new embedding
        embedding = await self.generate_embedding(text)

        # Cache result
        await self.cache_embedding(text_hash, org_id, embedding)

        return embedding
