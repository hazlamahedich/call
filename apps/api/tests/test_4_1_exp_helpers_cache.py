"""[4.1-EXP] Helper functions, cache I/O, source normalization"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.compliance.dnc_provider import DncCheckResult, validate_e164


# ============================================================
# [4.1-EXP-UNIT] validate_e164 edge cases
# ============================================================


@pytest.mark.p0
def test_4_1_exp_validate_whitespace_stripped():
    assert validate_e164("  +12025551234  ") == "+12025551234"


@pytest.mark.p2
def test_4_1_exp_validate_tab_prefix():
    assert validate_e164("\t+12025551234") == "+12025551234"


# ============================================================
# [4.1-EXP-UNIT] DncCheckResult defaults
# ============================================================


@pytest.mark.p2
def test_4_1_exp_check_result_defaults():
    r = DncCheckResult(phone_number="+12025551234")
    assert r.is_blocked is False
    assert r.result == "clear"
    assert r.source == ""
    assert r.response_time_ms == 0
    assert r.raw_response is None


@pytest.mark.p2
def test_4_1_exp_check_result_blocked():
    r = DncCheckResult(
        phone_number="+12025551234",
        is_blocked=True,
        source="national_dnc",
        result="blocked",
        response_time_ms=42,
    )
    assert r.is_blocked is True


# ============================================================
# [4.1-EXP-UNIT] _normalize_source (AC: 3)
# ============================================================


@pytest.mark.p2
def test_4_1_exp_normalize_known_sources():
    from services.compliance.dnc import _normalize_source

    assert _normalize_source("national_dnc") == "national_dnc"
    assert _normalize_source("state_dnc") == "state_dnc"
    assert _normalize_source("tenant_blocklist") == "tenant_blocklist"


@pytest.mark.p2
def test_4_1_exp_normalize_state_keyword():
    from services.compliance.dnc import _normalize_source

    assert _normalize_source("state_level") == "state_dnc"


@pytest.mark.p2
def test_4_1_exp_normalize_blocklist_keyword():
    from services.compliance.dnc import _normalize_source

    assert _normalize_source("internal_blocklist") == "tenant_blocklist"


@pytest.mark.p2
def test_4_1_exp_normalize_unknown_defaults_national():
    from services.compliance.dnc import _normalize_source

    assert _normalize_source("some_other_source") == "national_dnc"


# ============================================================
# [4.1-EXP-UNIT] _cache_key / _lock_key
# ============================================================


@pytest.mark.p2
def test_4_1_exp_cache_key_format():
    from services.compliance.dnc import _cache_key

    assert _cache_key("org1", "+12025551234") == "dnc:org1:+12025551234"


@pytest.mark.p2
def test_4_1_exp_lock_key_format():
    from services.compliance.dnc import _lock_key

    assert _lock_key("org1", "+12025551234") == "dnc:lock:org1:+12025551234"


# ============================================================
# [4.1-EXP-UNIT] _mask_phone edge cases
# ============================================================


@pytest.mark.p2
def test_4_1_exp_mask_phone_short():
    from services.compliance.dnc import _mask_phone

    assert _mask_phone("+1") == "***"
    assert _mask_phone("") == "***"


@pytest.mark.p2
def test_4_1_exp_mask_phone_exact_boundary():
    from services.compliance.dnc import _mask_phone

    assert _mask_phone("1234") == "***"
    assert _mask_phone("123") == "***"
    assert _mask_phone("12345") == "123***45"


# ============================================================
# [4.1-EXP-UNIT] _read_cache resilience
# ============================================================


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_exp_read_cache_none_redis():
    from services.compliance.dnc import _read_cache

    result = await _read_cache(None, "dnc:org:+12025551234")
    assert result is None


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_exp_read_cache_redis_error():
    from services.compliance.dnc import _read_cache

    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(side_effect=Exception("connection lost"))
    result = await _read_cache(mock_redis, "dnc:org:+12025551234")
    assert result is None


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_exp_read_cache_valid_json():
    from services.compliance.dnc import _read_cache

    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(
        return_value=json.dumps({"result": "clear", "source": "cache"})
    )
    result = await _read_cache(mock_redis, "dnc:org:+12025551234")
    assert result["result"] == "clear"


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_exp_read_cache_empty_string():
    from services.compliance.dnc import _read_cache

    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value="")
    result = await _read_cache(mock_redis, "dnc:org:+12025551234")
    assert result is None


# ============================================================
# [4.1-EXP-UNIT] _write_cache resilience
# ============================================================


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_exp_write_cache_none_redis():
    from services.compliance.dnc import _write_cache

    await _write_cache(None, "key", {"result": "clear"}, 3600)


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_exp_write_cache_redis_error():
    from services.compliance.dnc import _write_cache

    mock_redis = MagicMock()
    mock_redis.setex = AsyncMock(side_effect=Exception("write failed"))
    await _write_cache(mock_redis, "key", {"result": "clear"}, 3600)
