"""[4.1] check_dnc_realtime & scrub_leads_batch — ACs 3, 4, 5"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.compliance.dnc_provider import DncCheckResult
from services.compliance.exceptions import ComplianceBlockError
from helpers.dnc_helpers import make_mock_redis, make_mock_session
from tests.mocks.mock_dnc_provider import MockDncProvider


# ============================================================
# [4.1-UNIT-030..038] check_dnc_realtime (ACs: 4, 5)
# ============================================================


@pytest.mark.asyncio
@pytest.mark.p1
async def test_4_1_unit_030_cache_hit_clear():
    # Given: Redis cache has a "clear" result for this phone
    # When: check_dnc_realtime is called
    # Then: cached result is returned without provider call
    mock_redis, cache, _ = make_mock_redis(
        cache={
            "dnc:org1:+12025551234": json.dumps(
                {
                    "result": "clear",
                    "source": "national_dnc",
                    "checked_at": "2026-04-10T00:00:00Z",
                }
            )
        }
    )
    mock_session = make_mock_session()

    with (
        patch("services.compliance.dnc._provider", MockDncProvider()),
        patch("services.compliance.dnc._circuit_breaker") as mock_cb,
    ):
        mock_cb.is_available = AsyncMock(return_value=True)
        from services.compliance.dnc import check_dnc_realtime

        result = await check_dnc_realtime(
            mock_session, "+12025551234", "org1", mock_redis
        )
    assert result.result == "clear"
    assert not result.is_blocked


@pytest.mark.asyncio
@pytest.mark.p1
async def test_4_1_unit_031_cache_hit_blocked():
    # Given: Redis cache has a "blocked" result for this phone
    # When: check_dnc_realtime is called
    # Then: cached blocked result is returned
    mock_redis, cache, _ = make_mock_redis(
        cache={
            "dnc:org1:+12025559999": json.dumps(
                {
                    "result": "blocked",
                    "source": "national_dnc",
                    "checked_at": "2026-04-10T00:00:00Z",
                }
            )
        }
    )
    mock_session = make_mock_session()

    with (
        patch("services.compliance.dnc._provider", MockDncProvider()),
        patch("services.compliance.dnc._circuit_breaker") as mock_cb,
    ):
        mock_cb.is_available = AsyncMock(return_value=True)
        from services.compliance.dnc import check_dnc_realtime

        result = await check_dnc_realtime(
            mock_session, "+12025559999", "org1", mock_redis
        )
    assert result.is_blocked
    assert result.result == "blocked"


@pytest.mark.asyncio
@pytest.mark.p0
async def test_4_1_unit_035_fail_closed_on_provider_error():
    # Given: DNC provider returns error, circuit breaker is available
    # When: pre-dial DNC check is performed in fail-closed mode
    # Then: ComplianceBlockError is raised with DNC_PROVIDER_UNAVAILABLE
    mock_redis, _, _ = make_mock_redis()
    mock_session = make_mock_session()

    with (
        patch("services.compliance.dnc._provider", MockDncProvider(should_fail=True)),
        patch("services.compliance.dnc._circuit_breaker") as mock_cb,
    ):
        mock_cb.is_available = AsyncMock(return_value=True)
        mock_cb.record_failure = AsyncMock()
        from services.compliance.dnc import check_dnc_realtime

        with pytest.raises(ComplianceBlockError) as exc_info:
            await check_dnc_realtime(mock_session, "+12025551234", "org1", mock_redis)
        assert exc_info.value.code == "DNC_PROVIDER_UNAVAILABLE"


@pytest.mark.asyncio
@pytest.mark.p1
async def test_4_1_unit_036_no_redis_provider_fallback():
    # Given: no Redis client
    # When: check_dnc_realtime is called
    # Then: falls through to provider which returns "clear"
    mock_redis, _, _ = make_mock_redis()
    mock_session = make_mock_session()

    with (
        patch("services.compliance.dnc._provider", MockDncProvider()),
        patch("services.compliance.dnc._circuit_breaker") as mock_cb,
    ):
        mock_cb.is_available = AsyncMock(return_value=True)
        mock_cb.record_success = AsyncMock()
        from services.compliance.dnc import check_dnc_realtime

        result = await check_dnc_realtime(mock_session, "+12025551234", "org1", None)
    assert result.result == "clear"


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_unit_037_fail_open_mode_returns_error_not_raises():
    # Given: failing provider and fail_closed=False
    # When: check_dnc_realtime is called
    # Then: returns error result instead of raising
    mock_redis, _, _ = make_mock_redis()
    mock_session = make_mock_session()

    with (
        patch("services.compliance.dnc._provider", MockDncProvider(should_fail=True)),
        patch("services.compliance.dnc._circuit_breaker") as mock_cb,
    ):
        mock_cb.is_available = AsyncMock(return_value=True)
        mock_cb.record_failure = AsyncMock()
        from services.compliance.dnc import check_dnc_realtime

        result = await check_dnc_realtime(
            mock_session, "+12025551234", "org1", mock_redis, fail_closed=False
        )
    assert result.result == "error"
    assert not result.is_blocked


# ============================================================
# [4.1-UNIT-040] scrub_leads_batch (AC: 3)
# ============================================================


@pytest.mark.asyncio
@pytest.mark.p1
async def test_4_1_unit_040_all_leads_clear():
    # Given: 3 leads with no blocked numbers
    # When: scrub_leads_batch is called
    # Then: summary shows 3 total, 0 blocked
    mock_session = make_mock_session()
    mock_result = MagicMock()
    mock_result.fetchall = MagicMock(
        return_value=[(1, "+12025551234"), (2, "+12025559999"), (3, "+12025550000")]
    )
    mock_session.execute = AsyncMock(return_value=mock_result)

    with (
        patch("services.compliance.dnc._provider", MockDncProvider()),
        patch("services.compliance.dnc._circuit_breaker") as mock_cb,
        patch("services.compliance.dnc.check_dnc_realtime") as mock_check,
    ):
        mock_cb.is_available = AsyncMock(return_value=True)
        mock_check.return_value = DncCheckResult(
            phone_number="+12025551234", is_blocked=False, source="mock", result="clear"
        )
        from services.compliance.dnc import scrub_leads_batch

        summary = await scrub_leads_batch(mock_session, "org1", [1, 2, 3], None)
    assert summary.total == 3
    assert summary.blocked == 0
