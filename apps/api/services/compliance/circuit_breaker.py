from __future__ import annotations

import json
import logging
import time
from typing import Optional

import redis.asyncio as redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings

logger = logging.getLogger(__name__)


class DncCircuitBreaker:
    def __init__(
        self,
        threshold: int | None = None,
        open_sec: int | None = None,
    ) -> None:
        self._threshold = threshold or settings.DNC_CIRCUIT_BREAKER_THRESHOLD
        self._open_sec = open_sec or settings.DNC_CIRCUIT_OPEN_SEC

    def _keys(self, org_id: str) -> tuple[str, str, str]:
        base = f"dnc:circuit:{org_id}"
        return f"{base}:state", f"{base}:failures", f"{base}:opened_at"

    async def is_available(
        self, org_id: str, redis_client: redis.Redis | None = None
    ) -> bool:
        if redis_client is None:
            return True
        try:
            state_key, _, opened_at_key = self._keys(org_id)
            state = await redis_client.get(state_key)
            if state is None or state == b"closed" or state == "closed":
                return True
            if state == b"half_open" or state == "half_open":
                return True
            if state == b"open" or state == "open":
                opened_at_raw = await redis_client.get(opened_at_key)
                if opened_at_raw is None:
                    return True
                opened_at = float(opened_at_raw)
                if time.time() - opened_at > self._open_sec:
                    await redis_client.set(state_key, "half_open", ex=60)
                    return True
                return False
        except Exception as e:
            logger.warning(
                "Circuit breaker state check failed",
                extra={"code": "CIRCUIT_BREAKER_ERROR", "error": str(e)},
            )
            return True
        return True

    async def record_success(
        self, org_id: str, redis_client: redis.Redis | None = None
    ) -> None:
        if redis_client is None:
            return
        try:
            state_key, failures_key, _ = self._keys(org_id)
            await redis_client.delete(failures_key)
            await redis_client.set(state_key, "closed", ex=60)
        except Exception:
            pass

    async def record_failure(
        self, org_id: str, redis_client: redis.Redis | None = None
    ) -> None:
        if redis_client is None:
            return
        try:
            state_key, failures_key, opened_at_key = self._keys(org_id)
            count = await redis_client.incr(failures_key)
            await redis_client.expire(failures_key, 60)
            if count >= self._threshold:
                await redis_client.set(state_key, "open", ex=60)
                await redis_client.set(opened_at_key, str(time.time()), ex=60)
                logger.warning(
                    "DNC circuit breaker opened",
                    extra={
                        "code": "DNC_CIRCUIT_OPENED",
                        "org_id": org_id,
                        "failure_count": count,
                    },
                )
        except Exception:
            pass
