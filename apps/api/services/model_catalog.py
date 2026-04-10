"""OpenRouter model catalog integration.

Fetches, caches, and queries the OpenRouter model catalog for:
- Valid model name verification
- Per-model pricing (prompt + completion cost per token)
- Provider-aware cost computation from actual usage data
- Cost-optimized model recommendations

The catalog is cached locally with a configurable TTL. Falls back to
built-in pricing for OpenAI and Gemini when OpenRouter is unavailable.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"
_CATALOG_CACHE_KEY = "openrouter:model_catalog"
_DEFAULT_CACHE_TTL = 3600


@dataclass
class ModelPricing:
    model_id: str
    name: str
    provider: str
    context_length: int = 0
    prompt_cost_per_mtok: float = 0.0
    completion_cost_per_mtok: float = 0.0
    embedding_cost_per_mtok: float = 0.0

    def compute_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        prompt_cost = (prompt_tokens / 1_000_000) * self.prompt_cost_per_mtok
        completion_cost = (
            completion_tokens / 1_000_000
        ) * self.completion_cost_per_mtok
        return round(prompt_cost + completion_cost, 8)


@dataclass
class ModelCatalog:
    models: dict[str, ModelPricing] = field(default_factory=dict)
    fetched_at: float = 0.0
    source: str = "unknown"

    def get(self, model_id: str) -> Optional[ModelPricing]:
        return self.models.get(model_id)

    def is_valid_model(self, model_id: str) -> bool:
        return model_id in self.models

    def list_models(
        self,
        *,
        provider: str | None = None,
        capability: str | None = None,
        min_context: int = 0,
    ) -> list[ModelPricing]:
        results = list(self.models.values())
        if provider:
            results = [m for m in results if m.provider == provider]
        if min_context:
            results = [m for m in results if m.context_length >= min_context]
        if capability == "embedding":
            results = [m for m in results if m.embedding_cost_per_mtok > 0]
        elif capability == "chat":
            results = [m for m in results if m.completion_cost_per_mtok > 0]
        return sorted(results, key=lambda m: m.prompt_cost_per_mtok)

    def find_cheapest(
        self,
        *,
        provider: str | None = None,
        min_context: int = 0,
    ) -> Optional[ModelPricing]:
        chat_models = self.list_models(
            provider=provider, capability="chat", min_context=min_context
        )
        return chat_models[0] if chat_models else None


_BUILTIN_PRICING: dict[str, dict] = {
    "gpt-4o-mini": {
        "name": "GPT-4o Mini",
        "provider": "openai",
        "context_length": 128000,
        "prompt_cost_per_mtok": 0.15,
        "completion_cost_per_mtok": 0.60,
    },
    "gpt-4o": {
        "name": "GPT-4o",
        "provider": "openai",
        "context_length": 128000,
        "prompt_cost_per_mtok": 2.50,
        "completion_cost_per_mtok": 10.00,
    },
    "gpt-4-turbo": {
        "name": "GPT-4 Turbo",
        "provider": "openai",
        "context_length": 128000,
        "prompt_cost_per_mtok": 10.00,
        "completion_cost_per_mtok": 30.00,
    },
    "gpt-3.5-turbo": {
        "name": "GPT-3.5 Turbo",
        "provider": "openai",
        "context_length": 16385,
        "prompt_cost_per_mtok": 0.50,
        "completion_cost_per_mtok": 1.50,
    },
    "text-embedding-3-small": {
        "name": "Text Embedding 3 Small",
        "provider": "openai",
        "context_length": 8191,
        "prompt_cost_per_mtok": 0.02,
        "completion_cost_per_mtok": 0.0,
        "embedding_cost_per_mtok": 0.02,
    },
    "text-embedding-3-large": {
        "name": "Text Embedding 3 Large",
        "provider": "openai",
        "context_length": 8191,
        "prompt_cost_per_mtok": 0.13,
        "completion_cost_per_mtok": 0.0,
        "embedding_cost_per_mtok": 0.13,
    },
    "text-embedding-ada-002": {
        "name": "Ada 002 Embedding",
        "provider": "openai",
        "context_length": 8191,
        "prompt_cost_per_mtok": 0.10,
        "completion_cost_per_mtok": 0.0,
        "embedding_cost_per_mtok": 0.10,
    },
    "gemini-2.0-flash": {
        "name": "Gemini 2.0 Flash",
        "provider": "google",
        "context_length": 1048576,
        "prompt_cost_per_mtok": 0.10,
        "completion_cost_per_mtok": 0.40,
    },
    "gemini-2.0-flash-lite": {
        "name": "Gemini 2.0 Flash Lite",
        "provider": "google",
        "context_length": 1048576,
        "prompt_cost_per_mtok": 0.075,
        "completion_cost_per_mtok": 0.30,
    },
    "gemini-1.5-pro": {
        "name": "Gemini 1.5 Pro",
        "provider": "google",
        "context_length": 2097152,
        "prompt_cost_per_mtok": 1.25,
        "completion_cost_per_mtok": 5.00,
    },
    "gemini-1.5-flash": {
        "name": "Gemini 1.5 Flash",
        "provider": "google",
        "context_length": 1048576,
        "prompt_cost_per_mtok": 0.075,
        "completion_cost_per_mtok": 0.30,
    },
    "gemini-embedding-001": {
        "name": "Gemini Embedding 001",
        "provider": "google",
        "context_length": 8192,
        "prompt_cost_per_mtok": 0.0,
        "completion_cost_per_mtok": 0.0,
        "embedding_cost_per_mtok": 0.0,
    },
}


def _builtin_catalog() -> ModelCatalog:
    models = {}
    for model_id, data in _BUILTIN_PRICING.items():
        models[model_id] = ModelPricing(
            model_id=model_id,
            name=data["name"],
            provider=data["provider"],
            context_length=data.get("context_length", 0),
            prompt_cost_per_mtok=data.get("prompt_cost_per_mtok", 0.0),
            completion_cost_per_mtok=data.get("completion_cost_per_mtok", 0.0),
            embedding_cost_per_mtok=data.get("embedding_cost_per_mtok", 0.0),
        )
    return ModelCatalog(models=models, fetched_at=time.time(), source="builtin")


_catalog_instance: ModelCatalog | None = None
_catalog_lock = asyncio.Lock()


async def get_catalog(
    *,
    api_key: str | None = None,
    redis_client=None,
    cache_ttl: int = _DEFAULT_CACHE_TTL,
    force_refresh: bool = False,
) -> ModelCatalog:
    """Get the model catalog, fetching from OpenRouter if needed."""
    global _catalog_instance

    if not force_refresh and _catalog_instance is not None:
        age = time.time() - _catalog_instance.fetched_at
        if age < cache_ttl:
            return _catalog_instance

    if not force_refresh and redis_client is not None:
        cached = await _try_redis_catalog(redis_client)
        if cached is not None:
            _catalog_instance = cached
            return cached

    if api_key:
        fetched = await _fetch_openrouter_catalog(api_key)
        if fetched is not None:
            if redis_client is not None:
                await _store_redis_catalog(redis_client, fetched, cache_ttl)
            _catalog_instance = fetched
            return fetched

    if _catalog_instance is not None:
        return _catalog_instance

    _catalog_instance = _builtin_catalog()
    return _catalog_instance


async def _fetch_openrouter_catalog(api_key: str) -> ModelCatalog | None:
    url = f"{_OPENROUTER_API_BASE}/models"
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.warning("openrouter_catalog_fetch_failed: %s", str(e)[:200])
        return None

    models = {}
    for entry in data.get("data", []):
        model_id = entry.get("id", "")
        if not model_id:
            continue
        pricing = entry.get("pricing", {})
        prompt_cost = _safe_float(pricing.get("prompt", "0"))
        completion_cost = _safe_float(pricing.get("completion", "0"))
        context_length = entry.get("context_length", 0) or 0
        top_provider = entry.get("top_provider", {})
        provider_name = top_provider.get("provider_name", "unknown")

        models[model_id] = ModelPricing(
            model_id=model_id,
            name=entry.get("name", model_id),
            provider=provider_name,
            context_length=context_length,
            prompt_cost_per_mtok=prompt_cost,
            completion_cost_per_mtok=completion_cost,
        )

    for model_id, data in _BUILTIN_PRICING.items():
        if model_id not in models:
            models[model_id] = ModelPricing(
                model_id=model_id,
                name=data["name"],
                provider=data["provider"],
                context_length=data.get("context_length", 0),
                prompt_cost_per_mtok=data.get("prompt_cost_per_mtok", 0.0),
                completion_cost_per_mtok=data.get("completion_cost_per_mtok", 0.0),
                embedding_cost_per_mtok=data.get("embedding_cost_per_mtok", 0.0),
            )

    logger.info(
        "openrouter_catalog_loaded: %d models fetched",
        len(models),
    )
    return ModelCatalog(models=models, fetched_at=time.time(), source="openrouter")


async def _try_redis_catalog(redis_client) -> ModelCatalog | None:
    try:
        raw = await redis_client.get(_CATALOG_CACHE_KEY)
        if not raw:
            return None
        data = json.loads(raw)
        models = {}
        for model_id, m in data.get("models", {}).items():
            models[model_id] = ModelPricing(**m)
        return ModelCatalog(
            models=models,
            fetched_at=data.get("fetched_at", 0),
            source=data.get("source", "redis"),
        )
    except Exception as e:
        logger.debug("redis_catalog_read_failed: %s", str(e)[:100])
        return None


async def _store_redis_catalog(redis_client, catalog: ModelCatalog, ttl: int) -> None:
    try:
        data = {
            "models": {
                mid: {
                    "model_id": m.model_id,
                    "name": m.name,
                    "provider": m.provider,
                    "context_length": m.context_length,
                    "prompt_cost_per_mtok": m.prompt_cost_per_mtok,
                    "completion_cost_per_mtok": m.completion_cost_per_mtok,
                    "embedding_cost_per_mtok": m.embedding_cost_per_mtok,
                }
                for mid, m in catalog.models.items()
            },
            "fetched_at": catalog.fetched_at,
            "source": catalog.source,
        }
        await redis_client.setex(_CATALOG_CACHE_KEY, ttl, json.dumps(data))
    except Exception as e:
        logger.debug("redis_catalog_write_failed: %s", str(e)[:100])


def compute_cost(
    model_id: str,
    prompt_tokens: int,
    completion_tokens: int,
    catalog: ModelCatalog | None = None,
) -> float:
    if catalog is None:
        catalog = _builtin_catalog()
    pricing = catalog.get(model_id)
    if pricing is not None:
        return pricing.compute_cost(prompt_tokens, completion_tokens)

    builtin = _BUILTIN_PRICING.get(model_id)
    if builtin:
        p_cost = (prompt_tokens / 1_000_000) * builtin.get("prompt_cost_per_mtok", 0)
        c_cost = (completion_tokens / 1_000_000) * builtin.get(
            "completion_cost_per_mtok", 0
        )
        return round(p_cost + c_cost, 8)

    return 0.0


def _safe_float(val) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0
