"""Shared test helpers for Story 4.1 DNC compliance tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock


def make_mock_redis(cache=None, state=None):
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


def make_mock_session():
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
