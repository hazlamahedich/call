"""Cache invalidation registry for systematic invalidation across all caching layers.

Provides:
- Event-based cache invalidation (on KB update, script change, etc.)
- Centralized registry of all cache key patterns
- Atomic multi-key invalidation
"""

import logging
from enum import Enum
from typing import Optional

import redis.asyncio as redis

from config.settings import settings

logger = logging.getLogger(__name__)


class CacheDomain(str, Enum):
    SCRIPT_GENERATION = "script_gen"
    KNOWLEDGE_SEARCH = "kb_search"
    PRESET_SAMPLES = "preset_samples"
    MODEL_CATALOG = "model_catalog"
    DNC_REGISTRY = "dnc_registry"
    VARIABLE_RESOLUTION = "var_resolve"
    EMBEDDING = "embedding"


class InvalidationEvent(str, Enum):
    KNOWLEDGE_BASE_UPDATED = "kb_updated"
    KNOWLEDGE_BASE_DELETED = "kb_deleted"
    SCRIPT_UPDATED = "script_updated"
    SCRIPT_DELETED = "script_deleted"
    PRESET_CHANGED = "preset_changed"
    MODEL_CONFIG_CHANGED = "model_config_changed"
    LEAD_UPDATED = "lead_updated"
    DNC_BLOCKLIST_CHANGED = "dnc_changed"
    AGENT_CONFIG_CHANGED = "agent_changed"


_EVENT_DOMAIN_MAP: dict[InvalidationEvent, list[CacheDomain]] = {
    InvalidationEvent.KNOWLEDGE_BASE_UPDATED: [
        CacheDomain.KNOWLEDGE_SEARCH,
        CacheDomain.SCRIPT_GENERATION,
        CacheDomain.EMBEDDING,
    ],
    InvalidationEvent.KNOWLEDGE_BASE_DELETED: [
        CacheDomain.KNOWLEDGE_SEARCH,
        CacheDomain.SCRIPT_GENERATION,
        CacheDomain.EMBEDDING,
    ],
    InvalidationEvent.SCRIPT_UPDATED: [
        CacheDomain.SCRIPT_GENERATION,
        CacheDomain.VARIABLE_RESOLUTION,
    ],
    InvalidationEvent.SCRIPT_DELETED: [
        CacheDomain.SCRIPT_GENERATION,
        CacheDomain.VARIABLE_RESOLUTION,
    ],
    InvalidationEvent.PRESET_CHANGED: [
        CacheDomain.PRESET_SAMPLES,
    ],
    InvalidationEvent.MODEL_CONFIG_CHANGED: [
        CacheDomain.MODEL_CATALOG,
        CacheDomain.SCRIPT_GENERATION,
    ],
    InvalidationEvent.LEAD_UPDATED: [
        CacheDomain.VARIABLE_RESOLUTION,
        CacheDomain.SCRIPT_GENERATION,
    ],
    InvalidationEvent.DNC_BLOCKLIST_CHANGED: [
        CacheDomain.DNC_REGISTRY,
    ],
    InvalidationEvent.AGENT_CONFIG_CHANGED: [
        CacheDomain.SCRIPT_GENERATION,
        CacheDomain.PRESET_SAMPLES,
    ],
}


class CacheInvalidator:
    """Centralized cache invalidation for all caching layers.

    Usage:
        invalidator = CacheInvalidator(redis_client)
        await invalidator.invalidate(
            InvalidationEvent.KNOWLEDGE_BASE_UPDATED,
            org_id="org_abc",
            context_keys=["kb:42"],
        )
    """

    def __init__(self, redis_client: Optional[redis.Redis] = None) -> None:
        self._redis = redis_client

    async def invalidate(
        self,
        event: InvalidationEvent,
        org_id: str,
        context_keys: Optional[list[str]] = None,
    ) -> int:
        domains = _EVENT_DOMAIN_MAP.get(event, [])
        if not domains:
            return 0

        patterns: list[str] = []
        for domain in domains:
            base = f"cache:{domain}:{org_id}:*"
            patterns.append(base)
            if context_keys:
                for ck in context_keys:
                    patterns.append(f"cache:{domain}:{org_id}:{ck}*")
                    patterns.append(f"cache:{domain}:{org_id}:{ck}")

        total_deleted = 0
        if self._redis:
            try:
                for pattern in patterns:
                    keys = []
                    async for key in self._redis.scan_iter(match=pattern, count=100):
                        keys.append(key)
                    if keys:
                        deleted = await self._redis.delete(*keys)
                        total_deleted += deleted
            except Exception as e:
                logger.warning(
                    "Cache invalidation failed",
                    extra={
                        "code": "CACHE_INVALIDATION_ERROR",
                        "event": event.value,
                        "org_id": org_id,
                        "error": str(e),
                    },
                )
                return 0

        if total_deleted > 0:
            logger.info(
                "Cache invalidated",
                extra={
                    "code": "CACHE_INVALIDATED",
                    "event": event.value,
                    "org_id": org_id,
                    "domains": [d.value for d in domains],
                    "keys_deleted": total_deleted,
                },
            )

        return total_deleted

    async def invalidate_domain(
        self,
        domain: CacheDomain,
        org_id: str,
    ) -> int:
        if not self._redis:
            return 0

        pattern = f"cache:{domain.value}:{org_id}:*"
        total_deleted = 0
        try:
            keys = []
            async for key in self._redis.scan_iter(match=pattern, count=100):
                keys.append(key)
            if keys:
                total_deleted = await self._redis.delete(*keys)
        except Exception as e:
            logger.warning(
                "Domain cache invalidation failed",
                extra={
                    "code": "CACHE_DOMAIN_INVALIDATION_ERROR",
                    "domain": domain.value,
                    "org_id": org_id,
                    "error": str(e),
                },
            )
        return total_deleted


_redis_client: Optional[redis.Redis] = None
_invalidator: Optional[CacheInvalidator] = None


async def get_cache_invalidator() -> CacheInvalidator:
    global _redis_client, _invalidator
    if _invalidator is not None:
        return _invalidator

    try:
        _redis_client = redis.from_url(
            settings.REDIS_URL, encoding="utf-8", decode_responses=False
        )
    except Exception:
        _redis_client = None

    _invalidator = CacheInvalidator(_redis_client)
    return _invalidator


def reset_invalidator() -> None:
    global _redis_client, _invalidator
    _invalidator = None
    _redis_client = None
