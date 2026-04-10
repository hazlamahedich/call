"""[4.1-INT] Integration: trigger_outbound_call -> check_dnc_realtime wiring"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.compliance.dnc import check_dnc_realtime
from services.compliance.exceptions import ComplianceBlockError


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
    mock_result.rowcount = 0
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.flush = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.begin_nested = MagicMock(
        return_value=MagicMock(commit=AsyncMock(), rollback=AsyncMock())
    )
    return mock_session


# ============================================================
# [4.1-INT] check_dnc_realtime wiring — blocked by DNC
# ============================================================


@pytest.mark.asyncio
@pytest.mark.p0
async def test_4_1_int_realtime_blocked_raises_compliance_error():
    from tests.mocks.mock_dnc_provider import MockDncProvider

    mock_provider = MockDncProvider(blocked_numbers={"+12025551234"})
    mock_redis, _, _ = _make_mock_redis()
    mock_session = _make_mock_session()

    with patch("services.compliance.dnc._get_provider", return_value=mock_provider):
        result = await check_dnc_realtime(
            mock_session,
            "+12025551234",
            "org1",
            mock_redis,
            check_type="pre_dial",
            fail_closed=True,
        )

    assert result.is_blocked is True
    assert result.result == "blocked"


# ============================================================
# [4.1-INT] check_dnc_realtime wiring — clear passes through
# ============================================================


@pytest.mark.asyncio
@pytest.mark.p0
async def test_4_1_int_realtime_clear_allows_call():
    from tests.mocks.mock_dnc_provider import MockDncProvider

    mock_provider = MockDncProvider()
    mock_redis, _, _ = _make_mock_redis()
    mock_session = _make_mock_session()

    with patch("services.compliance.dnc._get_provider", return_value=mock_provider):
        result = await check_dnc_realtime(
            mock_session,
            "+12025559999",
            "org1",
            mock_redis,
            check_type="pre_dial",
            fail_closed=True,
        )

    assert result.is_blocked is False
    assert result.result == "clear"


# ============================================================
# [4.1-INT] Cache hit short-circuits provider call
# ============================================================


@pytest.mark.asyncio
@pytest.mark.p0
async def test_4_1_int_cache_hit_skips_provider():
    from tests.mocks.mock_dnc_provider import MockDncProvider

    mock_provider = MockDncProvider()
    mock_redis, _, _ = _make_mock_redis(
        cache={
            "dnc:org1:+12025551234": json.dumps(
                {"result": "blocked", "source": "cache"}
            )
        }
    )
    mock_session = _make_mock_session()

    with patch("services.compliance.dnc._get_provider", return_value=mock_provider):
        result = await check_dnc_realtime(
            mock_session,
            "+12025551234",
            "org1",
            mock_redis,
        )

    assert result.is_blocked is True
    assert result.source == "cache"
    assert mock_provider.lookup_count == 0


# ============================================================
# [4.1-INT] SLA timeout triggers fail-closed
# ============================================================


@pytest.mark.asyncio
@pytest.mark.p0
async def test_4_1_int_sla_timeout_fail_closed():
    with patch("services.compliance.dnc._get_provider") as mock_get:
        provider = MagicMock()

        async def _slow_lookup(phone_number):
            import asyncio

            await asyncio.sleep(2.0)
            from services.compliance.dnc_provider import DncCheckResult

            return DncCheckResult(
                phone_number=phone_number, is_blocked=False, result="clear"
            )

        provider.lookup = _slow_lookup
        mock_get.return_value = provider

        mock_redis, _, _ = _make_mock_redis()
        mock_session = _make_mock_session()

        with pytest.raises(ComplianceBlockError) as exc_info:
            await check_dnc_realtime(
                mock_session,
                "+12025551234",
                "org1",
                mock_redis,
                check_type="pre_dial",
                fail_closed=True,
            )

        assert exc_info.value.code == "DNC_PROVIDER_UNAVAILABLE"
        assert exc_info.value.source == "provider_timeout"


# ============================================================
# [4.1-INT] SLA timeout with fail_closed=False returns error result
# ============================================================


@pytest.mark.asyncio
@pytest.mark.p1
async def test_4_1_int_sla_timeout_fail_open():
    with patch("services.compliance.dnc._get_provider") as mock_get:
        provider = MagicMock()

        async def _slow_lookup(phone_number):
            import asyncio

            await asyncio.sleep(2.0)
            from services.compliance.dnc_provider import DncCheckResult

            return DncCheckResult(
                phone_number=phone_number, is_blocked=False, result="clear"
            )

        provider.lookup = _slow_lookup
        mock_get.return_value = provider

        mock_redis, _, _ = _make_mock_redis()
        mock_session = _make_mock_session()

        result = await check_dnc_realtime(
            mock_session,
            "+12025551234",
            "org1",
            mock_redis,
            check_type="pre_dial",
            fail_closed=False,
        )

        assert result.result == "error"
        assert result.source == "provider_timeout"


# ============================================================
# [4.1-INT] Provider error triggers circuit breaker recording
# ============================================================


@pytest.mark.asyncio
@pytest.mark.p1
async def test_4_1_int_provider_error_records_circuit_failure():
    from tests.mocks.mock_dnc_provider import MockDncProvider

    mock_provider = MockDncProvider(should_fail=True)
    mock_redis, _, state = _make_mock_redis()
    mock_session = _make_mock_session()

    with patch("services.compliance.dnc._get_provider", return_value=mock_provider):
        with pytest.raises(ComplianceBlockError) as exc_info:
            await check_dnc_realtime(
                mock_session,
                "+12025551234",
                "org1",
                mock_redis,
                check_type="pre_dial",
                fail_closed=True,
            )

    assert exc_info.value.code == "DNC_PROVIDER_UNAVAILABLE"
    failure_key = "dnc:circuit:org1:failures"
    assert state.get(failure_key, 0) >= 1


# ============================================================
# [4.1-INT] close_provider lifecycle
# ============================================================


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_int_close_provider_cleans_up():
    from services.compliance.dnc import close_provider, _get_provider
    from services.compliance.dnc_com_provider import DncComProvider

    _get_provider()

    with patch.object(DncComProvider, "close", new_callable=AsyncMock) as mock_close:
        await close_provider()
        mock_close.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_int_close_provider_idempotent():
    from services.compliance.dnc import close_provider

    import services.compliance.dnc as dnc_mod

    dnc_mod._provider = None

    await close_provider()
