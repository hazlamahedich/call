"""[4.1] Circuit Breaker — AC 8"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from services.compliance.circuit_breaker import DncCircuitBreaker
from helpers.dnc_helpers import make_mock_redis


# ============================================================
# [4.1-UNIT-020..024] Circuit Breaker (AC: 8)
# ============================================================


@pytest.mark.asyncio
@pytest.mark.p0
async def test_4_1_unit_020_circuit_opens_after_threshold():
    # Given: a circuit breaker with threshold=3
    # When: 3 consecutive failures are recorded
    # Then: circuit state transitions to "open"
    mock_redis, _cache, state = make_mock_redis()
    cb = DncCircuitBreaker(threshold=3, open_sec=30)
    org_id = "test_org"

    for _ in range(3):
        await cb.record_failure(org_id, mock_redis)

    assert _cache.get(f"dnc:circuit:{org_id}:state") in (b"open", "open")


@pytest.mark.asyncio
@pytest.mark.p1
async def test_4_1_unit_021_circuit_half_open_after_timeout():
    # Given: a circuit in "open" state with expired timeout
    # When: is_available is called
    # Then: circuit transitions to "half_open" and returns True
    mock_redis, cache, state = make_mock_redis()
    cb = DncCircuitBreaker(threshold=1, open_sec=0)
    org_id = "test_org_half_open"

    state[f"dnc:circuit:{org_id}:state"] = "open"
    state[f"dnc:circuit:{org_id}:opened_at"] = "0.0"

    available = await cb.is_available(org_id, mock_redis)
    assert available is True
    assert cache.get(f"dnc:circuit:{org_id}:state") in ("half_open", b"half_open")


@pytest.mark.asyncio
@pytest.mark.p1
async def test_4_1_unit_022_half_open_to_closed_on_success():
    # Given: a circuit in "half_open" state
    # When: record_success is called
    # Then: circuit transitions to "closed"
    mock_redis, cache, state = make_mock_redis()
    cb = DncCircuitBreaker(threshold=1, open_sec=30)
    org_id = "test_org_success"

    state[f"dnc:circuit:{org_id}:state"] = "half_open"
    await cb.record_success(org_id, mock_redis)

    assert cache.get(f"dnc:circuit:{org_id}:state") in ("closed", b"closed")


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_unit_023_no_redis_returns_available():
    # Given: no Redis client (None)
    # When: is_available is called
    # Then: returns True (fail-open for availability check)
    cb = DncCircuitBreaker(threshold=1)
    assert await cb.is_available("org", None) is True


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_unit_024_circuit_breaker_redis_error_returns_unavailable():
    # Given: Redis client that throws on get
    # When: is_available is called
    # Then: returns False (conservative on Redis errors)
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(side_effect=Exception("connection error"))
    cb = DncCircuitBreaker(threshold=1)
    assert await cb.is_available("org", mock_redis) is False
