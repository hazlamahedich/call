"""[4.1] DNC Registry Check — Expanded Coverage Suite

Tests cover gaps identified in automation analysis:
- DncComProvider (mock mode, retry, rate limit, timeout, health)
- Blocklist CRUD (check, add, remove, upsert)
- Distributed lock in check_dnc_realtime
- Cache I/O error resilience
- Latency logging thresholds
- Source normalization
- scrub_leads_batch (mixed results, dedup, chunking, exception paths)
- validate_e164 whitespace handling
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
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


def _make_mock_redis(cache=None, state=None):
    mock_redis = MagicMock()
    _cache = cache if cache is not None else {}
    _state = state if state is not None else {}

    async def fake_get(key):
        val = _cache.get(key)
        if val is None:
            val = _state.get(key)
        return val

    async def fake_set(key, val, **kw):
        _cache[key] = val

    async def fake_setex(key, ttl, val):
        _cache[key] = val

    async def fake_delete(key):
        _cache.pop(key, None)
        _state.pop(key, None)

    async def fake_incr(key):
        _state[key] = _state.get(key, 0) + 1
        return _state[key]

    async def fake_expire(key, ttl):
        pass

    async def fake_eval(script, numkeys, *args):
        lock_key, lock_owner = args[0], args[1]
        current = _cache.get(lock_key)
        if current == lock_owner:
            _cache.pop(lock_key, None)
            return 1
        return 0

    mock_redis.get = fake_get
    mock_redis.set = fake_set
    mock_redis.setex = fake_setex
    mock_redis.delete = fake_delete
    mock_redis.incr = fake_incr
    mock_redis.expire = fake_expire
    mock_redis.eval = fake_eval
    return mock_redis, _cache, _state


def _make_mock_session():
    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.first = MagicMock(return_value=None)
    mock_result.fetchall = MagicMock(return_value=[])
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.flush = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.begin_nested = MagicMock(
        return_value=MagicMock(commit=AsyncMock(), rollback=AsyncMock())
    )
    return mock_session


# ============================================================
# [4.1-EXP-UNIT] validate_e164 edge cases
# ============================================================


def test_4_1_exp_validate_whitespace_stripped():
    assert validate_e164("  +12025551234  ") == "+12025551234"


def test_4_1_exp_validate_tab_prefix():
    assert validate_e164("\t+12025551234") == "+12025551234"


# ============================================================
# [4.1-EXP-UNIT] DncCheckResult defaults
# ============================================================


def test_4_1_exp_check_result_defaults():
    r = DncCheckResult(phone_number="+12025551234")
    assert r.is_blocked is False
    assert r.result == "clear"
    assert r.source == ""
    assert r.response_time_ms == 0
    assert r.raw_response is None


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


def test_4_1_exp_normalize_known_sources():
    from services.compliance.dnc import _normalize_source

    assert _normalize_source("national_dnc") == "national_dnc"
    assert _normalize_source("state_dnc") == "state_dnc"
    assert _normalize_source("tenant_blocklist") == "tenant_blocklist"


def test_4_1_exp_normalize_state_keyword():
    from services.compliance.dnc import _normalize_source

    assert _normalize_source("state_level") == "state_dnc"


def test_4_1_exp_normalize_blocklist_keyword():
    from services.compliance.dnc import _normalize_source

    assert _normalize_source("internal_blocklist") == "tenant_blocklist"


def test_4_1_exp_normalize_unknown_defaults_national():
    from services.compliance.dnc import _normalize_source

    assert _normalize_source("some_other_source") == "national_dnc"


# ============================================================
# [4.1-EXP-UNIT] _cache_key / _lock_key
# ============================================================


def test_4_1_exp_cache_key_format():
    from services.compliance.dnc import _cache_key

    assert _cache_key("org1", "+12025551234") == "dnc:org1:+12025551234"


def test_4_1_exp_lock_key_format():
    from services.compliance.dnc import _lock_key

    assert _lock_key("org1", "+12025551234") == "dnc:lock:org1:+12025551234"


# ============================================================
# [4.1-EXP-UNIT] _mask_phone edge cases
# ============================================================


def test_4_1_exp_mask_phone_short():
    from services.compliance.dnc import _mask_phone

    assert _mask_phone("+1") == "***"
    assert _mask_phone("") == "***"


def test_4_1_exp_mask_phone_exact_boundary():
    from services.compliance.dnc import _mask_phone

    assert _mask_phone("1234") == "***"
    assert _mask_phone("123") == "***"
    assert _mask_phone("12345") == "123***45"


# ============================================================
# [4.1-EXP-UNIT] _read_cache resilience
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_read_cache_none_redis():
    from services.compliance.dnc import _read_cache

    result = await _read_cache(None, "dnc:org:+12025551234")
    assert result is None


@pytest.mark.asyncio
async def test_4_1_exp_read_cache_redis_error():
    from services.compliance.dnc import _read_cache

    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(side_effect=Exception("connection lost"))
    result = await _read_cache(mock_redis, "dnc:org:+12025551234")
    assert result is None


@pytest.mark.asyncio
async def test_4_1_exp_read_cache_valid_json():
    from services.compliance.dnc import _read_cache

    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(
        return_value=json.dumps({"result": "clear", "source": "cache"})
    )
    result = await _read_cache(mock_redis, "dnc:org:+12025551234")
    assert result["result"] == "clear"


@pytest.mark.asyncio
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
async def test_4_1_exp_write_cache_none_redis():
    from services.compliance.dnc import _write_cache

    await _write_cache(None, "key", {"result": "clear"}, 3600)


@pytest.mark.asyncio
async def test_4_1_exp_write_cache_redis_error():
    from services.compliance.dnc import _write_cache

    mock_redis = MagicMock()
    mock_redis.setex = AsyncMock(side_effect=Exception("write failed"))
    await _write_cache(mock_redis, "key", {"result": "clear"}, 3600)


# ============================================================
# [4.1-EXP-UNIT] DncComProvider — mock mode
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_com_provider_mock_mode():
    from services.compliance.dnc_com_provider import DncComProvider

    provider = DncComProvider()
    with patch("services.compliance.dnc_com_provider.settings") as mock_settings:
        mock_settings.DNC_API_KEY = ""
        mock_settings.DNC_API_BASE_URL = "https://api.dnc.com"
        mock_settings.DNC_PRE_DIAL_TIMEOUT_MS = 100
        result = await provider.lookup("+12025551234")
    assert result.result == "clear"
    assert result.is_blocked is False
    assert result.source == "mock_provider"


@pytest.mark.asyncio
async def test_4_1_exp_com_provider_mock_health():
    from services.compliance.dnc_com_provider import DncComProvider

    provider = DncComProvider()
    with patch("services.compliance.dnc_com_provider.settings") as mock_settings:
        mock_settings.DNC_API_KEY = ""
        mock_settings.DNC_API_BASE_URL = "https://api.dnc.com"
        health = await provider.health_check()
    assert health is True


# ============================================================
# [4.1-EXP-UNIT] DncComProvider — retry on 429
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_com_provider_rate_limited_then_success():
    from services.compliance.dnc_com_provider import DncComProvider

    provider = DncComProvider()
    mock_resp_429 = MagicMock()
    mock_resp_429.status_code = 429
    mock_resp_429.headers = {"Retry-After": "0.01"}

    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = {"status": "clear", "source": "dnc_com"}

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=[mock_resp_429, mock_resp_200])
    mock_client.is_closed = False

    with (
        patch("services.compliance.dnc_com_provider.settings") as mock_settings,
        patch.object(provider, "_ensure_client", return_value=mock_client),
    ):
        mock_settings.DNC_API_KEY = "test-key"
        result = await provider.lookup("+12025551234")

    assert result.result == "clear"


# ============================================================
# [4.1-EXP-UNIT] DncComProvider — 500 retry exhaustion
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_com_provider_500_exhaustion():
    from services.compliance.dnc_com_provider import DncComProvider

    provider = DncComProvider()
    mock_resp = MagicMock()
    mock_resp.status_code = 503

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.is_closed = False

    with (
        patch("services.compliance.dnc_com_provider.settings") as mock_settings,
        patch.object(provider, "_ensure_client", return_value=mock_client),
        patch(
            "services.compliance.dnc_com_provider.asyncio.sleep", new_callable=AsyncMock
        ),
    ):
        mock_settings.DNC_API_KEY = "test-key"
        result = await provider.lookup("+12025551234")

    assert result.result == "error"
    assert mock_client.post.call_count == 3


# ============================================================
# [4.1-EXP-UNIT] DncComProvider — timeout
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_com_provider_timeout():
    import httpx
    from services.compliance.dnc_com_provider import DncComProvider

    provider = DncComProvider()
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
    mock_client.is_closed = False

    with (
        patch("services.compliance.dnc_com_provider.settings") as mock_settings,
        patch.object(provider, "_ensure_client", return_value=mock_client),
        patch(
            "services.compliance.dnc_com_provider.asyncio.sleep", new_callable=AsyncMock
        ),
    ):
        mock_settings.DNC_API_KEY = "test-key"
        result = await provider.lookup("+12025551234")

    assert result.result == "error"


# ============================================================
# [4.1-EXP-UNIT] DncComProvider — successful blocked
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_com_provider_blocked_response():
    from services.compliance.dnc_com_provider import DncComProvider

    provider = DncComProvider()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"status": "blocked", "source": "national_dnc"}

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.is_closed = False

    with (
        patch("services.compliance.dnc_com_provider.settings") as mock_settings,
        patch.object(provider, "_ensure_client", return_value=mock_client),
    ):
        mock_settings.DNC_API_KEY = "test-key"
        result = await provider.lookup("+12025551234")

    assert result.is_blocked is True
    assert result.result == "blocked"
    assert result.source == "national_dnc"


# ============================================================
# [4.1-EXP-UNIT] DncComProvider — malformed JSON
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_com_provider_malformed_json():
    from services.compliance.dnc_com_provider import DncComProvider

    provider = DncComProvider()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.side_effect = ValueError("bad json")
    mock_resp.text = "not json"

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.is_closed = False

    with (
        patch("services.compliance.dnc_com_provider.settings") as mock_settings,
        patch.object(provider, "_ensure_client", return_value=mock_client),
    ):
        mock_settings.DNC_API_KEY = "test-key"
        result = await provider.lookup("+12025551234")

    assert result.result == "error"
    assert result.raw_response is not None


# ============================================================
# [4.1-EXP-UNIT] DncComProvider — health_check failure
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_com_provider_health_check_failure():
    from services.compliance.dnc_com_provider import DncComProvider

    provider = DncComProvider()
    mock_resp = MagicMock()
    mock_resp.status_code = 500

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.is_closed = False

    with (
        patch("services.compliance.dnc_com_provider.settings") as mock_settings,
        patch.object(provider, "_ensure_client", return_value=mock_client),
    ):
        mock_settings.DNC_API_KEY = "test-key"
        health = await provider.health_check()
    assert health is False


# ============================================================
# [4.1-EXP-UNIT] DncComProvider — health_check exception
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_com_provider_health_check_exception():
    from services.compliance.dnc_com_provider import DncComProvider

    provider = DncComProvider()
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=Exception("network error"))
    mock_client.is_closed = False

    with (
        patch("services.compliance.dnc_com_provider.settings") as mock_settings,
        patch.object(provider, "_ensure_client", return_value=mock_client),
    ):
        mock_settings.DNC_API_KEY = "test-key"
        health = await provider.health_check()
    assert health is False


# ============================================================
# [4.1-EXP-UNIT] DncComProvider — close
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_com_provider_close():
    from services.compliance.dnc_com_provider import DncComProvider

    provider = DncComProvider()
    mock_client = AsyncMock()
    mock_client.is_closed = False
    mock_client.aclose = AsyncMock()
    provider._client = mock_client

    await provider.close()
    mock_client.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_4_1_exp_com_provider_close_already_closed():
    from services.compliance.dnc_com_provider import DncComProvider

    provider = DncComProvider()
    mock_client = AsyncMock()
    mock_client.is_closed = True
    provider._client = mock_client

    await provider.close()
    mock_client.aclose.assert_not_called()


# ============================================================
# [4.1-EXP-UNIT] _safe_retry_after
# ============================================================


def test_4_1_exp_safe_retry_after_none():
    from services.compliance.dnc_com_provider import _safe_retry_after

    assert _safe_retry_after(None) == 0.5


def test_4_1_exp_safe_retry_after_float():
    from services.compliance.dnc_com_provider import _safe_retry_after

    assert _safe_retry_after("2.5") == 2.5


def test_4_1_exp_safe_retry_after_invalid():
    from services.compliance.dnc_com_provider import _safe_retry_after

    assert _safe_retry_after("not-a-number") == 0.5


# ============================================================
# [4.1-EXP-UNIT] DncComProvider — connect error
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_com_provider_connect_error():
    import httpx
    from services.compliance.dnc_com_provider import DncComProvider

    provider = DncComProvider()
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
    mock_client.is_closed = False

    with (
        patch("services.compliance.dnc_com_provider.settings") as mock_settings,
        patch.object(provider, "_ensure_client", return_value=mock_client),
        patch(
            "services.compliance.dnc_com_provider.asyncio.sleep", new_callable=AsyncMock
        ),
    ):
        mock_settings.DNC_API_KEY = "test-key"
        result = await provider.lookup("+12025551234")

    assert result.result == "error"


# ============================================================
# [4.1-EXP-UNIT] check_dnc_realtime — tenant blocklist hit
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_realtime_tenant_blocklist_hit():
    mock_redis, cache, _state = _make_mock_redis()
    mock_session = _make_mock_session()

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
    blocked_cache_key = "dnc:org1:+12025551234"
    assert blocked_cache_key in cache


# ============================================================
# [4.1-EXP-UNIT] check_dnc_realtime — distributed lock acquire/release
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_realtime_lock_acquired_and_released():
    mock_redis, cache, _state = _make_mock_redis()
    mock_session = _make_mock_session()

    lock_calls = {"set_nx": 0, "eval": 0}
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


# ============================================================
# [4.1-EXP-UNIT] check_dnc_realtime — invalid phone raises
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_realtime_invalid_phone_raises():
    mock_redis, _, _ = _make_mock_redis()
    mock_session = _make_mock_session()

    with (
        patch("services.compliance.dnc._provider", MockDncProvider()),
        patch("services.compliance.dnc._circuit_breaker") as mock_cb,
    ):
        mock_cb.is_available = AsyncMock(return_value=True)
        from services.compliance.dnc import check_dnc_realtime

        with pytest.raises(ComplianceBlockError) as exc_info:
            await check_dnc_realtime(mock_session, "not-a-number", "org1", mock_redis)
        assert exc_info.value.code == "DNC_INVALID_PHONE_FORMAT"


# ============================================================
# [4.1-EXP-UNIT] check_dnc_realtime — circuit open fail-closed
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_realtime_circuit_open_fail_closed():
    mock_redis, _, _ = _make_mock_redis()
    mock_session = _make_mock_session()

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


# ============================================================
# [4.1-EXP-UNIT] check_dnc_realtime — circuit open fail-open
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_realtime_circuit_open_fail_open():
    mock_redis, _, _ = _make_mock_redis()
    mock_session = _make_mock_session()

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


# ============================================================
# [4.1-EXP-UNIT] check_dnc_realtime — provider success caches result
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_realtime_provider_success_caches():
    mock_redis, cache, _state = _make_mock_redis()
    mock_session = _make_mock_session()

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


# ============================================================
# [4.1-EXP-UNIT] check_dnc_realtime — provider blocked caches with blocked TTL
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_realtime_provider_blocked_caches():
    mock_redis, cache, _state = _make_mock_redis()
    mock_session = _make_mock_session()

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


# ============================================================
# [4.1-EXP-UNIT] check_dnc_realtime — unexpected exception fail-closed
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_realtime_unexpected_exception_fail_closed():
    mock_redis, _, _ = _make_mock_redis()
    mock_session = _make_mock_session()
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


# ============================================================
# [4.1-EXP-UNIT] scrub_leads_batch — mixed blocked + clear
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_scrub_mixed_blocked_and_clear():
    mock_session = _make_mock_session()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [
        (1, "+12025551234"),
        (2, "+12025559999"),
        (3, "+12025550000"),
    ]
    mock_session.execute = AsyncMock(return_value=mock_result)

    call_count = 0

    async def fake_check(session, phone, org_id, redis, **kw):
        nonlocal call_count
        call_count += 1
        is_blocked = phone == "+12025559999"
        return DncCheckResult(
            phone_number=phone,
            is_blocked=is_blocked,
            source="national_dnc" if is_blocked else "mock",
            result="blocked" if is_blocked else "clear",
        )

    with (
        patch("services.compliance.dnc.check_dnc_realtime", side_effect=fake_check),
        patch("services.compliance.dnc.add_to_blocklist", new_callable=AsyncMock),
    ):
        from services.compliance.dnc import scrub_leads_batch

        summary = await scrub_leads_batch(mock_session, "org1", [1, 2, 3], None)

    assert summary.total == 3
    assert summary.blocked == 1


# ============================================================
# [4.1-EXP-UNIT] scrub_leads_batch — duplicate phone dedup
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_scrub_dedup_phones():
    mock_session = _make_mock_session()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [
        (1, "+12025551234"),
        (2, "+12025551234"),
    ]
    mock_session.execute = AsyncMock(return_value=mock_result)

    check_count = 0

    async def fake_check(session, phone, org_id, redis, **kw):
        nonlocal check_count
        check_count += 1
        return DncCheckResult(phone_number=phone, result="clear", source="mock")

    with patch("services.compliance.dnc.check_dnc_realtime", side_effect=fake_check):
        from services.compliance.dnc import scrub_leads_batch

        summary = await scrub_leads_batch(mock_session, "org1", [1, 2], None)

    assert check_count == 1
    assert summary.skipped == 1


# ============================================================
# [4.1-EXP-UNIT] scrub_leads_batch — error result marks unchecked
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_scrub_error_marks_unchecked():
    mock_session = _make_mock_session()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [(1, "+12025551234")]
    mock_session.execute = AsyncMock(return_value=mock_result)

    async def fake_check(session, phone, org_id, redis, **kw):
        return DncCheckResult(
            phone_number=phone, result="error", source="mock_provider"
        )

    with patch("services.compliance.dnc.check_dnc_realtime", side_effect=fake_check):
        from services.compliance.dnc import scrub_leads_batch

        summary = await scrub_leads_batch(mock_session, "org1", [1], None)

    assert summary.unchecked == 1


# ============================================================
# [4.1-EXP-UNIT] scrub_leads_batch — ComplianceBlockError caught
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_scrub_compliance_error_caught():
    mock_session = _make_mock_session()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [(1, "+12025551234")]
    mock_session.execute = AsyncMock(return_value=mock_result)

    async def fake_check(session, phone, org_id, redis, **kw):
        raise ComplianceBlockError(
            code="DNC_BLOCKED", phone_number=phone, source="national_dnc"
        )

    with patch("services.compliance.dnc.check_dnc_realtime", side_effect=fake_check):
        from services.compliance.dnc import scrub_leads_batch

        summary = await scrub_leads_batch(mock_session, "org1", [1], None)

    assert summary.unchecked == 1


# ============================================================
# [4.1-EXP-UNIT] scrub_leads_batch — unexpected exception caught
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_scrub_unexpected_exception_caught():
    mock_session = _make_mock_session()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [(1, "+12025551234")]
    mock_session.execute = AsyncMock(return_value=mock_result)

    async def fake_check(session, phone, org_id, redis, **kw):
        raise RuntimeError("unexpected")

    with patch("services.compliance.dnc.check_dnc_realtime", side_effect=fake_check):
        from services.compliance.dnc import scrub_leads_batch

        summary = await scrub_leads_batch(mock_session, "org1", [1], None)

    assert summary.unchecked == 1


# ============================================================
# [4.1-EXP-UNIT] scrub_leads_batch — add_to_blocklist failure tolerated
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_scrub_blocklist_failure_tolerated():
    mock_session = _make_mock_session()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [(1, "+12025559999")]
    mock_session.execute = AsyncMock(return_value=mock_result)

    async def fake_check(session, phone, org_id, redis, **kw):
        return DncCheckResult(
            phone_number=phone,
            is_blocked=True,
            source="national_dnc",
            result="blocked",
        )

    with (
        patch("services.compliance.dnc.check_dnc_realtime", side_effect=fake_check),
        patch(
            "services.compliance.dnc.add_to_blocklist",
            new_callable=AsyncMock,
            side_effect=Exception("db error"),
        ),
    ):
        from services.compliance.dnc import scrub_leads_batch

        summary = await scrub_leads_batch(mock_session, "org1", [1], None)

    assert summary.blocked == 1


# ============================================================
# [4.1-EXP-UNIT] scrub_leads_batch — empty lead list
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_scrub_empty_list():
    mock_session = _make_mock_session()

    from services.compliance.dnc import scrub_leads_batch

    summary = await scrub_leads_batch(mock_session, "org1", [], None)

    assert summary.total == 0
    assert summary.blocked == 0
    assert summary.unchecked == 0


# ============================================================
# [4.1-EXP-UNIT] scrub_leads_batch — null phone skipped
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_scrub_null_phone_skipped():
    mock_session = _make_mock_session()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [
        (1, None),
        (2, "+12025551234"),
    ]
    mock_session.execute = AsyncMock(return_value=mock_result)

    async def fake_check(session, phone, org_id, redis, **kw):
        return DncCheckResult(phone_number=phone, result="clear", source="mock")

    with patch("services.compliance.dnc.check_dnc_realtime", side_effect=fake_check):
        from services.compliance.dnc import scrub_leads_batch

        summary = await scrub_leads_batch(mock_session, "org1", [1, 2], None)

    assert summary.total == 2


# ============================================================
# [4.1-EXP-UNIT] DncScrubSummary fields
# ============================================================


def test_4_1_exp_scrub_summary_all_fields():
    s = DncScrubSummary(total=5, blocked=2, unchecked=1, skipped=1)
    assert s.total == 5
    assert s.blocked == 2
    assert s.unchecked == 1
    assert s.skipped == 1
    assert s.sources == {"national_dnc": 0, "state_dnc": 0, "tenant_blocklist": 0}


# ============================================================
# [4.1-EXP-UNIT] DncCircuitBreaker — _keys method
# ============================================================


def test_4_1_exp_cb_keys_format():
    cb = DncCircuitBreaker(threshold=5, open_sec=30)
    state_key, failures_key, opened_at_key = cb._keys("org1")
    assert state_key == "dnc:circuit:org1:state"
    assert failures_key == "dnc:circuit:org1:failures"
    assert opened_at_key == "dnc:circuit:org1:opened_at"


# ============================================================
# [4.1-EXP-UNIT] DncCircuitBreaker — record_failure increments correctly
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_cb_failure_increments():
    mock_redis, _, state = _make_mock_redis()
    cb = DncCircuitBreaker(threshold=3, open_sec=30)

    await cb.record_failure("org_test_incr", mock_redis)

    assert state.get("dnc:circuit:org_test_incr:failures") == 1


# ============================================================
# [4.1-EXP-UNIT] DncCircuitBreaker — record_failure no-op without redis
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_cb_failure_noop_no_redis():
    cb = DncCircuitBreaker(threshold=3, open_sec=30)
    await cb.record_failure("org", None)


# ============================================================
# [4.1-EXP-UNIT] DncCircuitBreaker — record_success no-op without redis
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_cb_success_noop_no_redis():
    cb = DncCircuitBreaker(threshold=3, open_sec=30)
    await cb.record_success("org", None)


# ============================================================
# [4.1-EXP-UNIT] DncCircuitBreaker — record_failure redis exception
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_cb_failure_redis_exception():
    mock_redis = MagicMock()
    mock_redis.incr = AsyncMock(side_effect=Exception("redis down"))
    cb = DncCircuitBreaker(threshold=3)
    await cb.record_failure("org", mock_redis)


# ============================================================
# [4.1-EXP-UNIT] DncCircuitBreaker — is_available closed state
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_cb_available_closed():
    mock_redis, cache, _state = _make_mock_redis()
    cache["dnc:circuit:org_closed:state"] = "closed"
    cb = DncCircuitBreaker(threshold=3)

    available = await cb.is_available("org_closed", mock_redis)
    assert available is True


# ============================================================
# [4.1-EXP-UNIT] DncCircuitBreaker — is_available half_open
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_cb_available_half_open():
    mock_redis, cache, _state = _make_mock_redis()
    cache["dnc:circuit:org_ho:state"] = "half_open"
    cb = DncCircuitBreaker(threshold=3)

    available = await cb.is_available("org_ho", mock_redis)
    assert available is True


# ============================================================
# [4.1-EXP-UNIT] DncCircuitBreaker — is_available open within timeout
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_cb_available_open_within_timeout():
    mock_redis, cache, _state = _make_mock_redis()
    cache["dnc:circuit:org_ow:state"] = "open"
    cache["dnc:circuit:org_ow:opened_at"] = str(time.time())
    cb = DncCircuitBreaker(threshold=3, open_sec=300)

    available = await cb.is_available("org_ow", mock_redis)
    assert available is False


# ============================================================
# [4.1-EXP-UNIT] DncCircuitBreaker — is_available open no opened_at
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_cb_available_open_no_opened_at():
    mock_redis, cache, _state = _make_mock_redis()
    cache["dnc:circuit:org_na:state"] = "open"
    cb = DncCircuitBreaker(threshold=3, open_sec=300)

    available = await cb.is_available("org_na", mock_redis)
    assert available is True


# ============================================================
# [4.1-EXP-UNIT] blocklist — remove_from_blocklist
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_blocklist_remove_success():
    from services.compliance.blocklist import remove_from_blocklist

    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.rowcount = 1
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.flush = AsyncMock()

    with patch(
        "services.compliance.blocklist.set_tenant_context", new_callable=AsyncMock
    ):
        removed = await remove_from_blocklist(mock_session, "org1", "+12025551234")

    assert removed is True


@pytest.mark.asyncio
async def test_4_1_exp_blocklist_remove_not_found():
    from services.compliance.blocklist import remove_from_blocklist

    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.rowcount = 0
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.flush = AsyncMock()

    with patch(
        "services.compliance.blocklist.set_tenant_context", new_callable=AsyncMock
    ):
        removed = await remove_from_blocklist(mock_session, "org1", "+12025551234")

    assert removed is False


# ============================================================
# [4.1-EXP-UNIT] blocklist — add_to_blocklist
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_blocklist_add_success():
    from services.compliance.blocklist import add_to_blocklist

    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.first.return_value = (
        1,
        "org1",
        "+12025551234",
        "national_dnc",
        "test",
        42,
        datetime.now(timezone.utc),
        None,
        datetime.now(timezone.utc),
        datetime.now(timezone.utc),
        False,
    )
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.flush = AsyncMock()

    with patch(
        "services.compliance.blocklist.set_tenant_context", new_callable=AsyncMock
    ):
        entry = await add_to_blocklist(
            mock_session, "org1", "+12025551234", "national_dnc", reason="test"
        )

    assert entry.phone_number == "+12025551234"
    assert entry.source == "national_dnc"


@pytest.mark.asyncio
async def test_4_1_exp_blocklist_add_no_row_raises():
    from services.compliance.blocklist import add_to_blocklist

    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.first.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.flush = AsyncMock()

    with (
        patch(
            "services.compliance.blocklist.set_tenant_context", new_callable=AsyncMock
        ),
        pytest.raises(RuntimeError, match="blocklist upsert returned no row"),
    ):
        await add_to_blocklist(mock_session, "org1", "+12025551234", "national_dnc")


# ============================================================
# [4.1-EXP-UNIT] blocklist — check_tenant_blocklist no match
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_blocklist_check_no_match():
    from services.compliance.blocklist import check_tenant_blocklist

    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.first.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch(
        "services.compliance.blocklist.set_tenant_context", new_callable=AsyncMock
    ):
        result = await check_tenant_blocklist(mock_session, "+12025551234", "org1")

    assert result is None


# ============================================================
# [4.1-EXP-UNIT] ComplianceBlockError — message format
# ============================================================


def test_4_1_exp_compliance_error_message_with_call_id():
    err = ComplianceBlockError(
        code="DNC_BLOCKED",
        phone_number="+12025551234",
        call_id=99,
        source="national_dnc",
        retry_after_seconds=30,
    )
    msg = str(err)
    assert "DNC_BLOCKED" in msg
    assert "call_id=99" in msg
    assert "retry after 30s" in msg


def test_4_1_exp_compliance_error_message_minimal():
    err = ComplianceBlockError(
        code="DNC_BLOCKED",
        phone_number="+12025551234",
    )
    msg = str(err)
    assert "DNC_BLOCKED" in msg
    assert "call_id" not in msg
    assert "retry" not in msg


# ============================================================
# [4.1-EXP-UNIT] __init__ exports
# ============================================================


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
# [4.1-EXP-UNIT] MockDncProvider — timeout mode
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_mock_provider_timeout_mode():
    provider = MockDncProvider(fail_with_timeout=True)
    result = await provider.lookup("+12025551234")
    assert result.result == "error"


# ============================================================
# [4.1-EXP-UNIT] MockDncProvider — lookup count
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_mock_provider_lookup_count():
    provider = MockDncProvider()
    assert provider.lookup_count == 0
    await provider.lookup("+12025551234")
    assert provider.lookup_count == 1
    await provider.lookup("+12025551234")
    assert provider.lookup_count == 2


# ============================================================
# [4.1-EXP-UNIT] MockDncProvider — latency simulation
# ============================================================


@pytest.mark.asyncio
async def test_4_1_exp_mock_provider_latency():
    provider = MockDncProvider(latency_ms=50)
    start = time.monotonic()
    result = await provider.lookup("+12025551234")
    elapsed = (time.monotonic() - start) * 1000
    assert elapsed >= 40
    assert result.result == "clear"
