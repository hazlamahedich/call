"""[4.1-EXP] check_dnc_realtime expanded — blocklist hit, lock, circuit, caching"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.compliance.exceptions import ComplianceBlockError
from services.compliance.dnc_provider import DncCheckResult
from helpers.dnc_helpers import make_mock_redis, make_mock_session
from tests.mocks.mock_dnc_provider import MockDncProvider


@pytest.mark.asyncio
@pytest.mark.p1
async def test_4_1_exp_realtime_tenant_blocklist_hit():
    # Given: phone is on tenant blocklist
    # When: check_dnc_realtime is called
    # Then: result is blocked with tenant_blocklist source and cache is populated
    mock_redis, cache, _ = make_mock_redis()
    mock_session = make_mock_session()
    mock_bl_entry = MagicMock()
    mock_bl_entry.source = "tenant_blocklist"

    with (
        patch("services.compliance.dnc._provider", MockDncProvider()),
        patch("services.compliance.dnc._circuit_breaker") as mock_cb,
        patch(
            "services.compliance.dnc.check_tenant_blocklist", return_value=mock_bl_entry
        ),
    ):
        mock_cb.is_available = AsyncMock(return_value=True)
        from services.compliance.dnc import check_dnc_realtime

        result = await check_dnc_realtime(
            mock_session, "+12025551234", "org1", mock_redis
        )
    assert result.is_blocked is True
    assert result.source == "tenant_blocklist"
    assert "dnc:org1:+12025551234" in cache


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_exp_realtime_lock_acquired_and_released():
    # Given: Redis with lock support
    # When: check_dnc_realtime is called
    # Then: distributed lock is acquired (SET NX) and released
    mock_redis, cache, _ = make_mock_redis()
    mock_session = make_mock_session()

    lock_calls = {"set_nx": 0}
    original_set = mock_redis.set

    async def tracked_set(key, val, **kw):
        if kw.get("nx"):
            lock_calls["set_nx"] += 1
            return True
        return await original_set(key, val)

    mock_redis.set = tracked_set

    with (
        patch("services.compliance.dnc._provider", MockDncProvider()),
        patch("services.compliance.dnc._circuit_breaker") as mock_cb,
    ):
        mock_cb.is_available = AsyncMock(return_value=True)
        mock_cb.record_success = AsyncMock()
        from services.compliance.dnc import check_dnc_realtime

        result = await check_dnc_realtime(
            mock_session, "+12025551234", "org1", mock_redis
        )
    assert result.result == "clear"
    assert lock_calls["set_nx"] == 1


@pytest.mark.asyncio
@pytest.mark.p0
async def test_4_1_exp_realtime_invalid_phone_raises():
    # Given: an invalid phone number format
    # When: check_dnc_realtime is called
    # Then: ComplianceBlockError with DNC_INVALID_PHONE_FORMAT is raised
    mock_redis, _, _ = make_mock_redis()
    mock_session = make_mock_session()

    with (
        patch("services.compliance.dnc._provider", MockDncProvider()),
        patch("services.compliance.dnc._circuit_breaker") as mock_cb,
    ):
        mock_cb.is_available = AsyncMock(return_value=True)
        from services.compliance.dnc import check_dnc_realtime

        with pytest.raises(ComplianceBlockError) as exc_info:
            await check_dnc_realtime(mock_session, "not-a-number", "org1", mock_redis)
        assert exc_info.value.code == "DNC_INVALID_PHONE_FORMAT"


@pytest.mark.asyncio
@pytest.mark.p0
async def test_4_1_exp_realtime_circuit_open_fail_closed():
    # Given: circuit breaker is open and fail_closed=True
    # When: check_dnc_realtime is called
    # Then: ComplianceBlockError with DNC_PROVIDER_UNAVAILABLE is raised
    mock_redis, _, _ = make_mock_redis()
    mock_session = make_mock_session()

    with (
        patch("services.compliance.dnc._provider", MockDncProvider()),
        patch("services.compliance.dnc._circuit_breaker") as mock_cb,
    ):
        mock_cb.is_available = AsyncMock(return_value=False)
        from services.compliance.dnc import check_dnc_realtime

        with pytest.raises(ComplianceBlockError) as exc_info:
            await check_dnc_realtime(
                mock_session, "+12025551234", "org1", mock_redis, fail_closed=True
            )
        assert exc_info.value.code == "DNC_PROVIDER_UNAVAILABLE"


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_exp_realtime_circuit_open_fail_open():
    mock_redis, _, _ = make_mock_redis()
    mock_session = make_mock_session()

    with (
        patch("services.compliance.dnc._provider", MockDncProvider()),
        patch("services.compliance.dnc._circuit_breaker") as mock_cb,
    ):
        mock_cb.is_available = AsyncMock(return_value=False)
        from services.compliance.dnc import check_dnc_realtime

        result = await check_dnc_realtime(
            mock_session, "+12025551234", "org1", mock_redis, fail_closed=False
        )
    assert result.result == "error"
    assert not result.is_blocked


@pytest.mark.asyncio
@pytest.mark.p1
async def test_4_1_exp_realtime_provider_success_caches():
    # Given: provider returns clear, no cache hit
    # When: check_dnc_realtime completes
    # Then: result is cached in Redis
    mock_redis, cache, _ = make_mock_redis()
    mock_session = make_mock_session()

    with (
        patch("services.compliance.dnc._provider", MockDncProvider()),
        patch("services.compliance.dnc._circuit_breaker") as mock_cb,
    ):
        mock_cb.is_available = AsyncMock(return_value=True)
        mock_cb.record_success = AsyncMock()
        from services.compliance.dnc import check_dnc_realtime

        result = await check_dnc_realtime(
            mock_session, "+12025551234", "org1", mock_redis
        )
    assert result.result == "clear"
    assert "dnc:org1:+12025551234" in cache


@pytest.mark.asyncio
@pytest.mark.p1
async def test_4_1_exp_realtime_provider_blocked_caches():
    # Given: provider returns blocked
    # When: check_dnc_realtime completes
    # Then: blocked result is cached
    mock_redis, cache, _ = make_mock_redis()
    mock_session = make_mock_session()

    with (
        patch(
            "services.compliance.dnc._provider",
            MockDncProvider(blocked_numbers={"+12025559999"}),
        ),
        patch("services.compliance.dnc._circuit_breaker") as mock_cb,
    ):
        mock_cb.is_available = AsyncMock(return_value=True)
        mock_cb.record_success = AsyncMock()
        from services.compliance.dnc import check_dnc_realtime

        result = await check_dnc_realtime(
            mock_session, "+12025559999", "org1", mock_redis
        )
    assert result.is_blocked is True
    assert "dnc:org1:+12025559999" in cache


@pytest.mark.asyncio
@pytest.mark.p1
async def test_4_1_exp_realtime_unexpected_exception_fail_closed():
    # Given: session.begin_nested raises RuntimeError
    # When: check_dnc_realtime is called in fail-closed mode
    # Then: ComplianceBlockError is raised
    mock_redis, _, _ = make_mock_redis()
    mock_session = make_mock_session()
    mock_session.begin_nested = MagicMock(side_effect=RuntimeError("nested tx failed"))

    with (
        patch("services.compliance.dnc._provider", MockDncProvider()),
        patch("services.compliance.dnc._circuit_breaker") as mock_cb,
    ):
        mock_cb.is_available = AsyncMock(return_value=True)
        mock_cb.record_failure = AsyncMock()
        from services.compliance.dnc import check_dnc_realtime

        with pytest.raises(ComplianceBlockError):
            await check_dnc_realtime(mock_session, "+12025551234", "org1", mock_redis)
