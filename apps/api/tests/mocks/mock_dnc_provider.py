from __future__ import annotations

import asyncio
import time
from typing import Optional

from services.compliance.dnc_provider import DncProvider, DncCheckResult


class MockDncProvider(DncProvider):
    def __init__(
        self,
        default_result: str = "clear",
        blocked_numbers: Optional[set[str]] = None,
        latency_ms: int = 0,
        should_fail: bool = False,
        fail_with_timeout: bool = False,
    ):
        self._default_result = default_result
        self._blocked_numbers = blocked_numbers or set()
        self._latency_ms = latency_ms
        self._should_fail = should_fail
        self._fail_with_timeout = fail_with_timeout
        self._lookup_count = 0

    @property
    def provider_name(self) -> str:
        return "mock_provider"

    @property
    def lookup_count(self) -> int:
        return self._lookup_count

    async def lookup(self, phone_number: str) -> DncCheckResult:
        self._lookup_count += 1
        start = time.monotonic()

        if self._latency_ms:
            await asyncio.sleep(self._latency_ms / 1000.0)

        if self._should_fail:
            elapsed = int((time.monotonic() - start) * 1000)
            return DncCheckResult(
                phone_number=phone_number,
                is_blocked=False,
                source=self.provider_name,
                result="error",
                response_time_ms=elapsed,
                raw_response={"error": "simulated_failure"},
            )

        if self._fail_with_timeout:
            import asyncio as aio

            await aio.sleep(10)
            elapsed = int((time.monotonic() - start) * 1000)
            return DncCheckResult(
                phone_number=phone_number,
                is_blocked=False,
                source=self.provider_name,
                result="error",
                response_time_ms=elapsed,
            )

        is_blocked = phone_number in self._blocked_numbers
        elapsed = int((time.monotonic() - start) * 1000)
        return DncCheckResult(
            phone_number=phone_number,
            is_blocked=is_blocked,
            source=self.provider_name,
            result="blocked" if is_blocked else "clear",
            response_time_ms=elapsed,
        )

    async def health_check(self) -> bool:
        return not self._should_fail
