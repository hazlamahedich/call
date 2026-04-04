"""Cache strategy abstraction for preset audio samples.

This module defines a protocol for cache implementations, allowing
explicit cache strategies and testability. Supports Redis and no-op
implementations for graceful degradation.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class CacheStrategy(ABC):
    """Abstract cache strategy protocol.

    Implementations can cache bytes with TTL expiration. All cache
    operations are async and resilient to failures.
    """

    @abstractmethod
    async def get(self, key: str) -> Optional[bytes]:
        """Retrieve cached value by key.

        Args:
            key: Cache key to retrieve

        Returns:
            Cached bytes or None if not found/error
        """
        pass

    @abstractmethod
    async def set(self, key: str, value: bytes, ttl_seconds: int) -> bool:
        """Store value with TTL expiration.

        Args:
            key: Cache key to store
            value: Bytes value to cache
            ttl_seconds: Time-to-live in seconds

        Returns:
            True if successfully cached, False on error
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete cached value.

        Args:
            key: Cache key to delete

        Returns:
            True if deleted, False on error
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close any open connections."""
        pass


class RedisCache(CacheStrategy):
    """Redis cache implementation with async operations.

    Provides resilient caching with automatic reconnection handling
    and comprehensive error logging.
    """

    def __init__(self, redis_client: redis.Redis) -> None:
        """Initialize Redis cache.

        Args:
            redis_client: Async Redis client instance
        """
        self.redis = redis_client

    async def get(self, key: str) -> Optional[bytes]:
        """Get value from Redis cache."""
        try:
            cached = await self.redis.get(key)
            if cached:
                logger.debug(
                    "Cache hit",
                    extra={"code": "CACHE_HIT", "key": key},
                )
                return cached
            return None
        except Exception as e:
            logger.warning(
                f"Redis cache read failed: {e}",
                extra={"code": "CACHE_READ_ERROR", "key": key},
            )
            return None

    async def set(self, key: str, value: bytes, ttl_seconds: int) -> bool:
        """Set value in Redis cache with TTL."""
        try:
            await self.redis.setex(key, ttl_seconds, value)
            logger.debug(
                "Cache set",
                extra={"code": "CACHE_SET", "key": key, "ttl": ttl_seconds},
            )
            return True
        except Exception as e:
            logger.warning(
                f"Redis cache write failed: {e}",
                extra={"code": "CACHE_WRITE_ERROR", "key": key},
            )
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from Redis cache."""
        try:
            await self.redis.delete(key)
            logger.debug(
                "Cache deleted",
                extra={"code": "CACHE_DELETE", "key": key},
            )
            return True
        except Exception as e:
            logger.warning(
                f"Redis cache delete failed: {e}",
                extra={"code": "CACHE_DELETE_ERROR", "key": key},
            )
            return False

    async def close(self) -> None:
        """Close Redis connection."""
        try:
            await self.redis.close()
            logger.debug("Redis cache connection closed")
        except Exception as e:
            logger.warning(f"Redis close error: {e}")


class NoOpCache(CacheStrategy):
    """No-operation cache for testing and degraded mode.

    Always returns None for gets and reports success for sets.
    Useful for testing and when cache is unavailable.
    """

    async def get(self, key: str) -> Optional[bytes]:  # noqa: ARG002 (key unused by design)
        """No-op get, always returns None."""
        return None

    async def set(self, key: str, value: bytes, ttl_seconds: int) -> bool:  # noqa: ARG002 (params unused by design)
        """No-op set, always reports success."""
        return True

    async def delete(self, key: str) -> bool:  # noqa: ARG002 (key unused by design)
        """No-op delete, always reports success."""
        return True

    async def close(self) -> None:
        """No-op close, nothing to clean up."""
        pass


async def create_cache_strategy(redis_url: Optional[str] = None) -> CacheStrategy:
    """Create appropriate cache strategy based on configuration.

    Args:
        redis_url: Redis connection URL or None for no-op cache

    Returns:
        CacheStrategy instance (RedisCache or NoOpCache)
    """
    if not redis_url:
        logger.info("Redis not configured, using NoOpCache")
        return NoOpCache()

    try:
        redis_client = await redis.from_url(redis_url, encoding="utf-8", decode_responses=False)
        return RedisCache(redis_client)
    except Exception as e:
        logger.warning(
            f"Failed to create Redis cache, falling back to NoOpCache: {e}",
            extra={"code": "CACHE_FALLBACK"},
        )
        return NoOpCache()
