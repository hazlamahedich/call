"""Unit tests for embedding service.

Tests embedding generation, batch processing, and Redis caching.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.embedding.service import EmbeddingService
from services.embedding.providers.base import EmbeddingProvider
from services.embedding.providers.openai_provider import OpenAIEmbeddingProvider


@pytest.mark.asyncio
class TestEmbeddingService:
    """Test suite for EmbeddingService."""

    @pytest.fixture
    def mock_provider(self):
        """Mock embedding provider."""
        provider = AsyncMock(spec=EmbeddingProvider)
        provider.embed = AsyncMock(return_value=[0.1, 0.2, 0.3] * 512)
        provider.embed_batch = AsyncMock(
            return_value=[[0.1] * 1536, [0.2] * 1536, [0.3] * 1536]
        )
        provider.model_name = "text-embedding-3-small"
        provider.dimensions = 1536
        return provider

    @pytest.fixture
    def embedding_service(self, mock_provider):
        """Create embedding service with mocked provider."""
        return EmbeddingService(provider=mock_provider)

    @pytest.mark.asyncio
    async def test_generate_embedding(self, embedding_service, mock_provider):
        """Test single embedding generation."""
        mock_provider.embed = AsyncMock(return_value=[0.1, 0.2, 0.3] * 512)

        embedding = await embedding_service.generate_embedding("Test text")

        assert len(embedding) == 1536
        assert all(isinstance(x, float) for x in embedding)

    @pytest.mark.asyncio
    async def test_generate_embeddings_batch(self, embedding_service, mock_provider):
        """Test batch embedding generation."""
        texts = ["Text one", "Text two", "Text three"]

        mock_provider.embed_batch = AsyncMock(
            return_value=[[0.1] * 1536, [0.2] * 1536, [0.3] * 1536]
        )

        embeddings = await embedding_service.generate_embeddings_batch(texts)

        assert len(embeddings) == 3
        assert all(len(emb) == 1536 for emb in embeddings)

    @pytest.mark.asyncio
    async def test_generate_embeddings_batch_too_large(self, embedding_service):
        """Test that batch size exceeding maximum raises error."""
        texts = ["Text"] * 101  # MAX_BATCH_SIZE is 100

        with pytest.raises(ValueError) as exc_info:
            await embedding_service.generate_embeddings_batch(texts)

        assert "exceeds maximum" in str(exc_info.value).lower()

    def test_compute_text_hash(self, embedding_service):
        """Test SHA-256 hash computation."""
        text1 = "Hello, World!"
        text2 = "Hello, World!"
        text3 = "Different text"

        hash1 = embedding_service.compute_text_hash(text1)
        hash2 = embedding_service.compute_text_hash(text2)
        hash3 = embedding_service.compute_text_hash(text3)

        # Same input produces same hash
        assert hash1 == hash2

        # Different input produces different hash
        assert hash1 != hash3

        # Hash is 64 characters (SHA-256 hex)
        assert len(hash1) == 64

    def test_build_cache_key(self, embedding_service):
        """Test cache key construction."""
        text_hash = "abc123"
        org_id = "org_123"

        cache_key = embedding_service._build_cache_key(text_hash, org_id)

        expected = "emb:v1:text-embedding-3-small:org_123:abc123"
        assert cache_key == expected

    @pytest.mark.asyncio
    async def test_get_cached_embedding_miss(self, embedding_service):
        """Test cache miss returns None."""
        # No Redis client configured
        result = await embedding_service.get_cached_embedding("hash123", "org_123")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_embedding_no_redis(self, embedding_service):
        """Test caching with no Redis client fails gracefully."""
        # No Redis client configured
        result = await embedding_service.cache_embedding(
            "hash123", "org_123", [0.1, 0.2, 0.3]
        )

        # Should return False (no Redis to cache to)
        assert result is False

    @pytest.mark.asyncio
    async def test_generate_with_cache_miss(self, embedding_service, mock_provider):
        """Test generate_with_cache when cache misses."""
        mock_provider.embed = AsyncMock(return_value=[0.1] * 1536)

        text = "Test text"
        org_id = "org_123"

        embedding = await embedding_service.generate_with_cache(text, org_id)

        assert len(embedding) == 1536
        # Verify provider was called (cache miss)
        mock_provider.embed.assert_called_once()


@pytest.mark.asyncio
class TestEmbeddingServiceWithRedis:
    """Test suite with mocked Redis client."""

    @pytest.fixture
    def mock_provider(self):
        """Mock embedding provider."""
        provider = AsyncMock(spec=EmbeddingProvider)
        provider.model_name = "text-embedding-3-small"
        provider.dimensions = 1536
        return provider

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        redis = AsyncMock()
        return redis

    @pytest.fixture
    def embedding_service(self, mock_provider, mock_redis):
        """Create embedding service with mocked Redis."""
        return EmbeddingService(provider=mock_provider, redis_client=mock_redis)

    @pytest.mark.asyncio
    async def test_get_cached_embedding_hit(self, embedding_service, mock_redis):
        """Test cache hit returns cached embedding."""
        # Mock Redis get response
        embedding_str = ",".join(str(x) for x in [0.1, 0.2, 0.3] * 512)
        mock_redis.get.return_value = embedding_str.encode("utf-8")

        result = await embedding_service.get_cached_embedding("hash123", "org_123")

        assert result is not None
        assert len(result) == 1536
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_embedding_success(self, embedding_service, mock_redis):
        """Test successful cache write."""
        embedding = [0.1, 0.2, 0.3] * 512  # 1536 dimensions

        result = await embedding_service.cache_embedding(
            "hash123", "org_123", embedding
        )

        assert result is True
        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_embedding_redis_error(self, embedding_service, mock_redis):
        """Test that Redis errors are handled gracefully (fail-open)."""
        # Mock Redis error
        mock_redis.setex.side_effect = Exception("Redis connection failed")

        result = await embedding_service.cache_embedding(
            "hash123", "org_123", [0.1, 0.2, 0.3]
        )

        # Should return False but not raise exception
        assert result is False

    @pytest.mark.asyncio
    async def test_get_cached_embedding_redis_error(
        self, embedding_service, mock_redis
    ):
        """Test that Redis get errors are handled gracefully."""
        # Mock Redis error
        mock_redis.get.side_effect = Exception("Redis connection failed")

        result = await embedding_service.get_cached_embedding("hash123", "org_123")

        # Should return None (fail-open to direct API)
        assert result is None

    @pytest.mark.asyncio
    async def test_generate_with_cache_hit(self, embedding_service, mock_redis):
        """Test generate_with_cache when cache hits."""
        # Mock Redis cache hit
        embedding_str = ",".join(str(x) for x in [0.1] * 1536)
        mock_redis.get.return_value = embedding_str.encode("utf-8")

        text = "Test text"
        org_id = "org_123"

        # Get cached embedding (simulated)
        text_hash = embedding_service.compute_text_hash(text)
        cache_key = embedding_service._build_cache_key(text_hash, org_id)

        # Verify cache key is correct
        expected_key = f"emb:v1:text-embedding-3-small:{org_id}:{text_hash}"
        assert cache_key == expected_key


@pytest.mark.asyncio
class TestEmbeddingServiceRetry:
    """Test retry logic for API failures."""

    @pytest.fixture
    def mock_provider_flaky(self):
        """Mock embedding provider that fails initially."""
        provider = AsyncMock(spec=EmbeddingProvider)
        provider.model_name = "text-embedding-3-small"
        provider.dimensions = 1536
        # First two calls fail, third succeeds
        call_count = [0]

        async def flaky_embed(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 3:
                raise Exception("API error")
            return [0.1] * 1536

        provider.embed = flaky_embed
        return provider

    @pytest.fixture
    def embedding_service(self, mock_provider_flaky):
        """Create embedding service."""
        return EmbeddingService(provider=mock_provider_flaky)

    @pytest.mark.asyncio
    async def test_generate_embedding_retry_success(self, embedding_service):
        """Test that retry logic eventually succeeds."""
        embedding = await embedding_service.generate_embedding("Test text")

        assert len(embedding) == 1536

    @pytest.mark.asyncio
    async def test_generate_embedding_retry_fails(self):
        """Test that retries are exhausted after MAX_RETRIES."""
        provider = AsyncMock(spec=EmbeddingProvider)
        provider.embed = AsyncMock(side_effect=Exception("Permanent failure"))
        provider.model_name = "text-embedding-3-small"

        service = EmbeddingService(provider=provider)

        with pytest.raises(Exception) as exc_info:
            await service.generate_embedding("Test text")

        assert "failed after" in str(exc_info.value).lower()
