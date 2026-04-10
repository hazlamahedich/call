"""[4.1-EXP] Circuit breaker expanded, MockDncProvider modes, exports, summary"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.compliance.circuit_breaker import DncCircuitBreaker
from services.compliance.dnc_provider import DncScrubSummary
from helpers.dnc_helpers import make_mock_redis
from tests.mocks.mock_dnc_provider import MockDncProvider


# ============================================================
# [4.1-EXP-UNIT] DncScrubSummary fields
# ============================================================


@pytest.mark.p3
def test_4_1_exp_scrub_summary_all_fields():
    s = DncScrubSummary(total=5, blocked=2, unchecked=1, skipped=1)
    assert s.total == 5
    assert s.blocked == 2
    assert s.unchecked == 1
    assert s.skipped == 1
    assert s.sources == {"national_dnc": 0, "state_dnc": 0, "tenant_blocklist": 0}


# ============================================================
# [4.1-EXP-UNIT] DncCircuitBreaker — expanded
# ============================================================


@pytest.mark.p2
def test_4_1_exp_cb_keys_format():
    cb = DncCircuitBreaker(threshold=5, open_sec=30)
    state_key, failures_key, opened_at_key = cb._keys("org1")
    assert state_key == "dnc:circuit:org1:state"
    assert failures_key == "dnc:circuit:org1:failures"
    assert opened_at_key == "dnc:circuit:org1:opened_at"


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_exp_cb_failure_increments():
    mock_redis, _, state = make_mock_redis()
    cb = DncCircuitBreaker(threshold=3, open_sec=30)
    await cb.record_failure("org_test_incr", mock_redis)
    assert state.get("dnc:circuit:org_test_incr:failures") == 1


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_exp_cb_failure_noop_no_redis():
    cb = DncCircuitBreaker(threshold=3, open_sec=30)
    await cb.record_failure("org", None)


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_exp_cb_success_noop_no_redis():
    cb = DncCircuitBreaker(threshold=3, open_sec=30)
    await cb.record_success("org", None)


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_exp_cb_failure_redis_exception():
    mock_redis = MagicMock()
    mock_redis.incr = AsyncMock(side_effect=Exception("redis down"))
    cb = DncCircuitBreaker(threshold=3)
    await cb.record_failure("org", mock_redis)


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_exp_cb_available_closed():
    mock_redis, cache, _ = make_mock_redis()
    cache["dnc:circuit:org_closed:state"] = "closed"
    cb = DncCircuitBreaker(threshold=3)
    available = await cb.is_available("org_closed", mock_redis)
    assert available is True


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_exp_cb_available_half_open():
    mock_redis, cache, _ = make_mock_redis()
    cache["dnc:circuit:org_ho:state"] = "half_open"
    cb = DncCircuitBreaker(threshold=3)
    available = await cb.is_available("org_ho", mock_redis)
    assert available is True


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_exp_cb_available_open_within_timeout():
    mock_redis, cache, _ = make_mock_redis()
    cache["dnc:circuit:org_ow:state"] = "open"
    cache["dnc:circuit:org_ow:opened_at"] = str(time.time())
    cb = DncCircuitBreaker(threshold=3, open_sec=300)
    available = await cb.is_available("org_ow", mock_redis)
    assert available is False


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_exp_cb_available_open_no_opened_at():
    mock_redis, cache, _ = make_mock_redis()
    cache["dnc:circuit:org_na:state"] = "open"
    cb = DncCircuitBreaker(threshold=3, open_sec=300)
    available = await cb.is_available("org_na", mock_redis)
    assert available is True


# ============================================================
# [4.1-EXP-UNIT] __init__ exports
# ============================================================


@pytest.mark.p3
def test_4_1_exp_public_api_exports():
    import services.compliance as pkg

    assert hasattr(pkg, "ComplianceBlockError")
    assert hasattr(pkg, "DncProvider")
    assert hasattr(pkg, "DncCheckResult")
    assert hasattr(pkg, "DncScrubSummary")
    assert hasattr(pkg, "InvalidPhoneFormatError")
    assert hasattr(pkg, "validate_e164")
    assert hasattr(pkg, "check_dnc_realtime")
    assert hasattr(pkg, "scrub_leads_batch")
    assert hasattr(pkg, "check_tenant_blocklist")
    assert hasattr(pkg, "add_to_blocklist")
    assert hasattr(pkg, "remove_from_blocklist")
    assert hasattr(pkg, "DncCircuitBreaker")


# ============================================================
# [4.1-EXP-UNIT] MockDncProvider — timeout mode (FIXED: patched sleep)
# ============================================================


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_exp_mock_provider_timeout_mode():
    # Given: MockDncProvider configured to simulate timeout
    # When: lookup is called
    # Then: returns error result (sleep is patched to avoid 10s delay)
    provider = MockDncProvider(fail_with_timeout=True)
    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await provider.lookup("+12025551234")
    assert result.result == "error"


# ============================================================
# [4.1-EXP-UNIT] MockDncProvider — lookup count
# ============================================================


@pytest.mark.asyncio
@pytest.mark.p3
async def test_4_1_exp_mock_provider_lookup_count():
    provider = MockDncProvider()
    assert provider.lookup_count == 0
    await provider.lookup("+12025551234")
    assert provider.lookup_count == 1
    await provider.lookup("+12025551234")
    assert provider.lookup_count == 2


# ============================================================
# [4.1-EXP-UNIT] MockDncProvider — latency (FIXED: verify sleep, not wall-clock)
# ============================================================


@pytest.mark.asyncio
@pytest.mark.p3
async def test_4_1_exp_mock_provider_latency():
    # Given: MockDncProvider with 50ms latency
    # When: lookup is called
    # Then: asyncio.sleep is called with correct duration
    provider = MockDncProvider(latency_ms=50)
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await provider.lookup("+12025551234")
    mock_sleep.assert_called_once_with(0.05)
    assert result.result == "clear"
