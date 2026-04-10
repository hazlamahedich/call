from __future__ import annotations

import logging
import time
from typing import Optional

import httpx

from config.settings import settings
from .dnc_provider import DncProvider, DncCheckResult

logger = logging.getLogger(__name__)


class DncComProvider(DncProvider):
    def __init__(self) -> None:
        self._client: Optional[httpx.AsyncClient] = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=settings.DNC_API_BASE_URL,
                timeout=httpx.Timeout(
                    max_connect=2.0,
                    max_read=settings.DNC_PRE_DIAL_TIMEOUT_MS / 1000.0,
                    max_write=2.0,
                    max_pool=2.0,
                ),
                headers={
                    "Authorization": f"Bearer {settings.DNC_API_KEY}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    @property
    def provider_name(self) -> str:
        return "dnc_com"

    async def lookup(self, phone_number: str) -> DncCheckResult:
        start = time.monotonic()

        if not settings.DNC_API_KEY:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return DncCheckResult(
                phone_number=phone_number,
                is_blocked=False,
                source="mock_provider",
                result="clear",
                response_time_ms=elapsed_ms,
            )

        client = await self._ensure_client()
        backoff = 0.5

        for attempt in range(3):
            try:
                resp = await client.post(
                    "/lookup",
                    json={"phone": phone_number},
                )
                elapsed_ms = int((time.monotonic() - start) * 1000)

                if resp.status_code == 429:
                    logger.warning(
                        "DNC provider rate limited",
                        extra={"code": "DNC_RATE_LIMITED", "attempt": attempt + 1},
                    )
                    if attempt < 2:
                        import asyncio

                        await asyncio.sleep(backoff)
                        backoff *= 2
                        continue
                    return DncCheckResult(
                        phone_number=phone_number,
                        is_blocked=False,
                        source=self.provider_name,
                        result="error",
                        response_time_ms=elapsed_ms,
                        raw_response={"status_code": 429, "error": "rate_limited"},
                    )

                if resp.status_code >= 500:
                    return DncCheckResult(
                        phone_number=phone_number,
                        is_blocked=False,
                        source=self.provider_name,
                        result="error",
                        response_time_ms=elapsed_ms,
                        raw_response={"status_code": resp.status_code},
                    )

                try:
                    data = resp.json()
                except Exception:
                    return DncCheckResult(
                        phone_number=phone_number,
                        is_blocked=False,
                        source=self.provider_name,
                        result="error",
                        response_time_ms=elapsed_ms,
                        raw_response={
                            "status_code": resp.status_code,
                            "body": resp.text[:200],
                        },
                    )

                is_blocked = data.get("status") == "blocked"
                return DncCheckResult(
                    phone_number=phone_number,
                    is_blocked=is_blocked,
                    source=data.get("source", self.provider_name),
                    result="blocked" if is_blocked else "clear",
                    response_time_ms=elapsed_ms,
                    raw_response=data,
                )

            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                elapsed_ms = int((time.monotonic() - start) * 1000)
                logger.warning(
                    "DNC provider request failed",
                    extra={"code": "DNC_PROVIDER_ERROR", "error": str(exc)},
                )
                return DncCheckResult(
                    phone_number=phone_number,
                    is_blocked=False,
                    source=self.provider_name,
                    result="error",
                    response_time_ms=elapsed_ms,
                )

        elapsed_ms = int((time.monotonic() - start) * 1000)
        return DncCheckResult(
            phone_number=phone_number,
            is_blocked=False,
            source=self.provider_name,
            result="error",
            response_time_ms=elapsed_ms,
        )

    async def health_check(self) -> bool:
        if not settings.DNC_API_KEY:
            return True
        try:
            client = await self._ensure_client()
            resp = await client.get("/health")
            return resp.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
