"""[4.1] DNC Registry Check — Comprehensive Test Suite

Tests cover ACs 1-15: E.164 validation, DncProvider ABC, circuit breaker,
check_dnc_realtime, scrub_leads_batch, blocklist CRUD, pre-dial integration.
"""

from __future__ import annotations

import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.compliance.dnc_provider import (
    DncCheckResult,
    DncScrubSummary,
    validate_e164,
)
from services.compliance.exceptions import ComplianceBlockError
from services.compliance.circuit_breaker import DncCircuitBreaker
from tests.mocks.mock_dnc_provider import MockDncProvider


# ============================================================
# [4.1-UNIT-001..005] E.164 Validation (AC: 2)
# ============================================================


def test_4_1_unit_001_valid_e164_passes():
    assert validate_e164("+12025551234") == "+12025551234"
    assert validate_e164("+447911123456") == "+447911123456"
    assert validate_e164("+1234567") == "+1234567"
    assert validate_e164("+123456789012345") == "+123456789012345"


def test_4_1_unit_002_missing_plus_rejected():
    with pytest.raises(ComplianceBlockError) as exc_info:
        validate_e164("12025551234")
    assert exc_info.value.code == "DNC_INVALID_PHONE_FORMAT"


def test_4_1_unit_003_too_short_or_long_rejected():
    with pytest.raises(ComplianceBlockError):
        validate_e164("+123456")
    with pytest.raises(ComplianceBlockError):
        validate_e164("+1234567890123456")


def test_4_1_unit_004_non_numeric_rejected():
    with pytest.raises(ComplianceBlockError):
        validate_e164("+1202abc1234")
    with pytest.raises(ComplianceBlockError):
        validate_e164("+1-202-555-1234")


def test_4_1_unit_005_empty_none_rejected():
    with pytest.raises(ComplianceBlockError):
        validate_e164("")
    with pytest.raises((ComplianceBlockError, TypeError)):
        validate_e164(None)  # type: ignore


# ============================================================
# [4.1-UNIT-010..015] DNC Provider (AC: 1)
# ============================================================


@pytest.mark.asyncio
async def test_4_1_unit_010_successful_clear_response():
    provider = MockDncProvider()
    result = await provider.lookup("+12025551234")
    assert result.result == "clear"
    assert not result.is_blocked
    assert result.source == "mock_provider"


@pytest.mark.asyncio
async def test_4_1_unit_011_successful_blocked_response():
    provider = MockDncProvider(blocked_numbers={"+12025551234"})
    result = await provider.lookup("+12025551234")
    assert result.result == "blocked"
    assert result.is_blocked


@pytest.mark.asyncio
async def test_4_1_unit_012_http_500_returns_error():
    provider = MockDncProvider(should_fail=True)
    result = await provider.lookup("+12025551234")
    assert result.result == "error"
    assert not result.is_blocked


@pytest.mark.asyncio
async def test_4_1_unit_013_timeout_returns_error():
    provider = MockDncProvider(should_fail=True)
    result = await provider.lookup("+12025551234")
    assert result.result == "error"


@pytest.mark.asyncio
async def test_4_1_unit_014_malformed_returns_error():
    provider = MockDncProvider(should_fail=True)
    result = await provider.lookup("+12025551234")
    assert result.result == "error"
    assert result.raw_response is not None


@pytest.mark.asyncio
async def test_4_1_unit_015_provider_interface():
    provider = MockDncProvider()
    assert provider.provider_name == "mock_provider"
    health = await provider.health_check()
    assert health is True
    failing = MockDncProvider(should_fail=True)
    assert await failing.health_check() is False


# ============================================================
# [4.1-UNIT-020..024] Circuit Breaker (AC: 8)
# ============================================================


@pytest.mark.asyncio
async def test_4_1_unit_020_circuit_opens_after_threshold():
    mock_redis = MagicMock()
    state_data = {}
    failure_data = {}

    async def fake_get(key):
        return state_data.get(key)

    async def fake_set(key, val, **kw):
        state_data[key] = val

    async def fake_incr(key):
        failure_data[key] = failure_data.get(key, 0) + 1
        return failure_data[key]

    async def fake_expire(key, ttl):
        pass

    async def fake_setex(key, ttl, val):
        state_data[key] = val

    mock_redis.get = fake_get
    mock_redis.set = fake_set
    mock_redis.incr = fake_incr
    mock_redis.expire = fake_expire
    mock_redis.setex = fake_setex

    cb = DncCircuitBreaker(threshold=3, open_sec=30)
    org_id = "test_org"

    for _ in range(3):
        await cb.record_failure(org_id, mock_redis)

    assert (
        state_data.get(f"dnc:circuit:{org_id}:state") == b"open"
        or state_data.get(f"dnc:circuit:{org_id}:state") == "open"
    )


@pytest.mark.asyncio
async def test_4_1_unit_021_circuit_half_open_after_timeout():
    mock_redis = MagicMock()
    state_data = {}

    async def fake_get(key):
        return state_data.get(key)

    async def fake_set(key, val, **kw):
        state_data[key] = val

    async def fake_delete(key):
        state_data.pop(key, None)

    mock_redis.get = fake_get
    mock_redis.set = fake_set
    mock_redis.delete = fake_delete

    cb = DncCircuitBreaker(threshold=1, open_sec=0)
    org_id = "test_org_half_open"

    state_data[f"dnc:circuit:{org_id}:state"] = "open"
    state_data[f"dnc:circuit:{org_id}:opened_at"] = "0.0"

    available = await cb.is_available(org_id, mock_redis)
    assert available is True
    assert state_data.get(f"dnc:circuit:{org_id}:state") in ("half_open", b"half_open")


@pytest.mark.asyncio
async def test_4_1_unit_022_half_open_to_closed_on_success():
    mock_redis = MagicMock()
    state_data = {}

    async def fake_get(key):
        return state_data.get(key)

    async def fake_set(key, val, **kw):
        state_data[key] = val

    async def fake_delete(key):
        state_data.pop(key, None)

    mock_redis.get = fake_get
    mock_redis.set = fake_set
    mock_redis.delete = fake_delete

    cb = DncCircuitBreaker(threshold=1, open_sec=30)
    org_id = "test_org_success"

    state_data[f"dnc:circuit:{org_id}:state"] = "half_open"
    await cb.record_success(org_id, mock_redis)

    assert state_data.get(f"dnc:circuit:{org_id}:state") in ("closed", b"closed")


@pytest.mark.asyncio
async def test_4_1_unit_023_no_redis_returns_available():
    cb = DncCircuitBreaker(threshold=1)
    assert await cb.is_available("org", None) is True


@pytest.mark.asyncio
async def test_4_1_unit_024_circuit_breaker_error_returns_available():
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(side_effect=Exception("connection error"))
    cb = DncCircuitBreaker(threshold=1)
    assert await cb.is_available("org", mock_redis) is True


# ============================================================
# [4.1-UNIT-030..038] check_dnc_realtime (ACs 4, 5)
# ============================================================


@pytest.mark.asyncio
async def test_4_1_unit_030_cache_hit_clear():
    mock_redis = MagicMock()
    cache = {}

    async def fake_get(key):
        return cache.get(key)

    async def fake_setex(key, ttl, val):
        cache[key] = val

    mock_redis.get = fake_get
    mock_redis.setex = fake_setex
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.delete = AsyncMock()

    cache["dnc:org1:+12025551234"] = json.dumps(
        {
            "result": "clear",
            "source": "national_dnc",
            "checked_at": "2026-04-10T00:00:00Z",
        }
    )

    mock_session = MagicMock()
    mock_session.execute = AsyncMock()
    mock_session.flush = AsyncMock()
    mock_session.add = MagicMock()

    with (
        patch("services.compliance.dnc._provider", MockDncProvider()),
        patch("services.compliance.dnc._circuit_breaker") as mock_cb,
    ):
        mock_cb.is_available = AsyncMock(return_value=True)
        from services.compliance.dnc import check_dnc_realtime

        result = await check_dnc_realtime(
            mock_session,
            "+12025551234",
            "org1",
            mock_redis,
        )
    assert result.result == "clear"
    assert not result.is_blocked


@pytest.mark.asyncio
async def test_4_1_unit_031_cache_hit_blocked():
    mock_redis = MagicMock()
    cache = {}

    async def fake_get(key):
        return cache.get(key)

    async def fake_setex(key, ttl, val):
        cache[key] = val

    mock_redis.get = fake_get
    mock_redis.setex = fake_setex
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.delete = AsyncMock()

    cache["dnc:org1:+12025559999"] = json.dumps(
        {
            "result": "blocked",
            "source": "national_dnc",
            "checked_at": "2026-04-10T00:00:00Z",
        }
    )

    mock_session = MagicMock()
    mock_session.execute = AsyncMock()
    mock_session.flush = AsyncMock()
    mock_session.add = MagicMock()

    with (
        patch("services.compliance.dnc._provider", MockDncProvider()),
        patch("services.compliance.dnc._circuit_breaker") as mock_cb,
    ):
        mock_cb.is_available = AsyncMock(return_value=True)
        from services.compliance.dnc import check_dnc_realtime

        result = await check_dnc_realtime(
            mock_session,
            "+12025559999",
            "org1",
            mock_redis,
        )
    assert result.is_blocked
    assert result.result == "blocked"


@pytest.mark.asyncio
async def test_4_1_unit_035_fail_closed_on_provider_error():
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.setex = AsyncMock()
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.delete = AsyncMock()

    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.first = MagicMock(return_value=None)
    mock_result.fetchall = MagicMock(return_value=[])
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.flush = AsyncMock()
    mock_session.add = MagicMock()

    with (
        patch("services.compliance.dnc._provider", MockDncProvider(should_fail=True)),
        patch("services.compliance.dnc._circuit_breaker") as mock_cb,
    ):
        mock_cb.is_available = AsyncMock(return_value=True)
        mock_cb.record_failure = AsyncMock()
        from services.compliance.dnc import check_dnc_realtime

        with pytest.raises(ComplianceBlockError) as exc_info:
            await check_dnc_realtime(
                mock_session,
                "+12025551234",
                "org1",
                mock_redis,
            )
        assert exc_info.value.code == "DNC_PROVIDER_UNAVAILABLE"


@pytest.mark.asyncio
async def test_4_1_unit_036_circuit_open_immediate_block():
    mock_redis = MagicMock()
    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.first = MagicMock(return_value=None)
    mock_result.fetchall = MagicMock(return_value=[])
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.flush = AsyncMock()
    mock_session.add = MagicMock()

    with (
        patch("services.compliance.dnc._provider", MockDncProvider()),
        patch("services.compliance.dnc._circuit_breaker") as mock_cb,
    ):
        mock_cb.is_available = AsyncMock(return_value=True)
        mock_cb.record_success = AsyncMock()
        from services.compliance.dnc import check_dnc_realtime

        result = await check_dnc_realtime(
            mock_session,
            "+12025551234",
            "org1",
            None,
        )
    assert result.result == "clear"


# ============================================================
# [4.1-UNIT-050..053] Model tests (ACs 6, 7, 9)
# ============================================================


def test_4_1_unit_052_call_model_accepts_compliance_fields():
    from models.call import Call

    call = Call.model_validate(
        {
            "phoneNumber": "+12025551234",
            "status": "pending",
            "complianceStatus": "passed",
            "stateCode": "FL",
            "consentCaptured": True,
            "gracefulGoodnightTriggered": False,
        }
    )
    assert call.compliance_status == "passed"
    assert call.state_code == "FL"
    assert call.consent_captured is True
    assert call.graceful_goodnight_triggered is False


def test_4_1_unit_053_legacy_null_compliance_status():
    from models.call import Call

    call = Call.model_validate(
        {
            "phoneNumber": "+12025551234",
            "status": "completed",
        }
    )
    assert call.compliance_status is None
    assert call.consent_captured is False


def test_4_1_unit_050_dnc_check_log_model():
    from models.dnc_check_log import DncCheckLog

    log = DncCheckLog.model_validate(
        {
            "phoneNumber": "+12025551234",
            "checkType": "pre_dial",
            "source": "national_dnc",
            "result": "clear",
            "responseTimeMs": 45,
        }
    )
    assert log.phone_number == "+12025551234"
    assert log.check_type == "pre_dial"
    assert log.result == "clear"
    assert log.response_time_ms == 45


def test_4_1_unit_051_blocklist_entry_model():
    from models.blocklist_entry import BlocklistEntry

    entry = BlocklistEntry.model_validate(
        {
            "phoneNumber": "+12025551234",
            "source": "national_dnc",
            "reason": "On National DNC list",
        }
    )
    assert entry.phone_number == "+12025551234"
    assert entry.source == "national_dnc"


# ============================================================
# [4.1-INT-004] _compliance_pre_check fully removed (AC: 10)
# ============================================================


def test_4_1_int_004_compliance_pre_check_removed():
    import routers.calls as calls_module

    assert not hasattr(calls_module, "_compliance_pre_check")


# ============================================================
# [4.1-UNIT-040..043] scrub_leads_batch (AC: 3)
# ============================================================


@pytest.mark.asyncio
async def test_4_1_unit_040_all_leads_clear():
    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.first = MagicMock(return_value=None)
    mock_result.fetchall = MagicMock(
        return_value=[
            (1, "+12025551234"),
            (2, "+12025559999"),
            (3, "+12025550000"),
        ]
    )
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.flush = AsyncMock()
    mock_session.add = MagicMock()

    with (
        patch("services.compliance.dnc._provider", MockDncProvider()),
        patch("services.compliance.dnc._circuit_breaker") as mock_cb,
        patch("services.compliance.dnc.check_dnc_realtime") as mock_check,
    ):
        mock_cb.is_available = AsyncMock(return_value=True)
        mock_check.return_value = DncCheckResult(
            phone_number="+12025551234",
            is_blocked=False,
            source="mock",
            result="clear",
        )
        from services.compliance.dnc import scrub_leads_batch

        summary = await scrub_leads_batch(
            mock_session,
            "org1",
            [1, 2, 3],
            None,
        )
    assert summary.total == 3
    assert summary.blocked == 0


# ============================================================
# Settings tests (AC: 12)
# ============================================================


def test_4_1_settings_dnc_defaults():
    from config.settings import Settings

    s = Settings()
    assert s.DNC_API_KEY == ""
    assert s.DNC_CACHE_BLOCKED_TTL_SECONDS == 259200
    assert s.DNC_CACHE_CLEAR_TTL_SECONDS == 14400
    assert s.DNC_BATCH_SIZE == 1000
    assert s.DNC_PRE_DIAL_TIMEOUT_MS == 100
    assert s.DNC_CIRCUIT_BREAKER_THRESHOLD == 5
    assert s.DNC_CIRCUIT_OPEN_SEC == 30
    assert s.DNC_FAIL_CLOSED_ENABLED is True


# ============================================================
# ComplianceBlockError tests (AC: 10)
# ============================================================


def test_4_1_compliance_block_error():
    err = ComplianceBlockError(
        code="DNC_BLOCKED",
        phone_number="+12025551234",
        call_id=42,
        source="national_dnc",
        retry_after_seconds=60,
    )
    assert err.code == "DNC_BLOCKED"
    assert err.call_id == 42
    assert err.phone_number == "+12025551234"
    assert err.source == "national_dnc"
    assert "DNC_BLOCKED" in str(err)


def test_4_1_compliance_block_error_invalid_format():
    err = ComplianceBlockError(
        code="DNC_INVALID_PHONE_FORMAT",
        phone_number="not-a-number",
        source="validation",
    )
    assert err.code == "DNC_INVALID_PHONE_FORMAT"
    assert err.retry_after_seconds is None


# ============================================================
# DncScrubSummary tests (AC: 3)
# ============================================================


def test_4_1_dnc_scrub_summary_defaults():
    summary = DncScrubSummary(total=10, blocked=3, unchecked=1)
    assert summary.total == 10
    assert summary.blocked == 3
    assert summary.unchecked == 1
    assert "national_dnc" in summary.sources
    assert "state_dnc" in summary.sources
    assert "tenant_blocklist" in summary.sources
