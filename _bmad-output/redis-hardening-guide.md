# Redis Infrastructure Hardening Guide

**Epic:** Epic 2 → Epic 3 Transition
**Date:** 2026-04-04
**Status:** Infrastructure Hardening
**Priority:** Medium (Redis is now runtime dependency from Story 2.6)

---

## Overview

Story 2.6 introduced Redis for preset sample caching. Redis is now a runtime dependency in the critical path for performance. This guide covers hardening Redis for production readiness.

## Current State

**Usage:** PresetSampleService (Story 2.6)
**Pattern:** Cache-aside with fallback on failure
**Graceful Degradation:** Yes (falls through to generation on Redis failure)

---

## Hardening Checklist

### 1. Connection Pooling ✅

**Current:** Single connection
**Target:** Connection pool with limits

```python
# services/cache_strategy.py
from redis.asyncio import ConnectionPool, Redis

class CacheStrategy:
    def __init__(self):
        self._pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=20,  # Adjust based on load
            socket_timeout=5.0,
            socket_connect_timeout=5.0,
            retry_on_timeout=True,
            health_check_interval=30,
        )
        self._redis = Redis(connection_pool=self._pool)
```

### 2. Health Checks ✅

**Current:** No health monitoring
**Target:** Active health checks with circuit breaker

```python
# services/cache_strategy.py
async def health_check(self) -> bool:
    """Check Redis connectivity."""
    try:
        await self._redis.ping()
        return True
    except Exception as e:
        logger.error(
            "Redis health check failed",
            extra={"code": "REDIS_HEALTH_CHECK_FAILED", "error": str(e)}
        )
        return False
```

### 3. Retry Logic ✅

**Current:** No retries
**Target:** Exponential backoff retry

```python
# services/cache_strategy.py
import asyncio

async def _get_with_retry(self, key: str, max_retries: int = 3) -> str | None:
    """Get value with exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            return await self._redis.get(key)
        except RedisError as e:
            if attempt == max_retries - 1:
                logger.error(
                    "Redis get failed after retries",
                    extra={"code": "REDIS_GET_FAILED", "key": key, "error": str(e)}
                )
                return None

            backoff = 2 ** attempt  # 1s, 2s, 4s
            logger.warning(
                "Redis get failed, retrying",
                extra={
                    "code": "REDIS_GET_RETRY",
                    "key": key,
                    "attempt": attempt + 1,
                    "backoff": backoff
                }
            )
            await asyncio.sleep(backoff)

    return None
```

### 4. Timeout Configuration ✅

**Current:** Default timeouts
**Target:** Explicit timeouts for all operations

```python
# services/cache_strategy.py
async def get(self, key: str, timeout: float = 2.0) -> str | None:
    """Get value with explicit timeout."""
    try:
        return await asyncio.wait_for(
            self._get_with_retry(key),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.error(
            "Redis get timed out",
            extra={"code": "REDIS_GET_TIMEOUT", "key": key, "timeout": timeout}
        )
        return None
```

### 5. Monitoring & Metrics ✅

**Current:** Basic logging
**Target:** Prometheus metrics

```python
# services/cache_strategy.py
from prometheus_client import Counter, Histogram

redis_get_counter = Counter(
    'redis_get_requests_total',
    'Total Redis GET requests',
    ['status']  # 'hit', 'miss', 'error'
)

redis_get_latency = Histogram(
    'redis_get_latency_seconds',
    'Redis GET latency',
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

async def get(self, key: str) -> str | None:
    """Get value with metrics."""
    start = time.monotonic()

    try:
        value = await self._redis.get(key)
        if value:
            redis_get_counter.labels(status='hit').inc()
        else:
            redis_get_counter.labels(status='miss').inc()
        return value
    except Exception as e:
        redis_get_counter.labels(status='error').inc()
        logger.error("Redis get failed", extra={"code": "REDIS_GET_ERROR", "error": str(e)})
        return None
    finally:
        redis_get_latency.observe(time.monotonic() - start)
```

### 6. Graceful Degradation ✅

**Current:** Basic fallback
**Target:** Circuit breaker pattern

```python
# services/cache_strategy.py
class RedisCircuitBreaker:
    """Circuit breaker for Redis failures."""

    def __init__(self, failure_threshold: int = 5, timeout_sec: int = 60):
        self._failure_threshold = failure_threshold
        self._timeout_sec = timeout_sec
        self._failures = 0
        self._last_failure_time = None
        self._state = "closed"  # closed, open, half-open

    def record_success(self):
        self._failures = 0
        self._state = "closed"

    def record_failure(self):
        self._failures += 1
        self._last_failure_time = time.monotonic()

        if self._failures >= self._failure_threshold:
            self._state = "open"
            logger.error(
                "Redis circuit breaker opened",
                extra={"code": "REDIS_CIRCUIT_OPEN", "failures": self._failures}
            )

    def can_attempt(self) -> bool:
        if self._state == "closed":
            return True

        if self._state == "open":
            if time.monotonic() - self._last_failure_time > self._timeout_sec:
                self._state = "half-open"
                return True
            return False

        return True  # half-open
```

### 7. Configuration Management ✅

**Current:** Hardcoded defaults
**Target:** Environment-based configuration

```python
# config/settings.py
class RedisSettings(BaseSettings):
    """Redis configuration."""

    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 20
    REDIS_SOCKET_TIMEOUT: float = 5.0
    REDIS_CONNECT_TIMEOUT: float = 5.0
    REDIS_RETRY_ON_TIMEOUT: bool = True
    REDIS_HEALTH_CHECK_INTERVAL: int = 30
    REDIS_CIRCUIT_FAILURE_THRESHOLD: int = 5
    REDIS_CIRCUIT_TIMEOUT_SEC: int = 60

    # Cache TTL settings
    REDIS_PRESET_SAMPLE_TTL_SEC: int = 86400  # 24 hours
    REDIS_SESSION_TTL_SEC: int = 3600  # 1 hour

    class Config:
        env_prefix = "REDIS_"
```

### 8. Health Endpoint ✅

**Current:** No health check
**Target:** Dedicated health endpoint

```python
# routers/health.py
@router.get("/health/redis")
async def redis_health(redis: CacheStrategy = Depends(get_cache)):
    """Check Redis health."""
    is_healthy = await redis.health_check()

    return {
        "status": "ok" if is_healthy else "unhealthy",
        "timestamp": datetime.utcnow().isoformat(),
        "details": {
            "connection_pool_size": redis._pool.connection_pool.connection_pool_size if is_healthy else None,
        }
    }
```

### 9. Backup & Recovery ✅

**Current:** No persistence strategy
**Target:** RDB + AOF persistence

```bash
# redis.conf
# Enable RDB snapshots
save 900 1
save 300 10
save 60 10000

# Enable AOF
appendonly yes
appendfsync everysec

# Persistence file locations
dir /var/lib/redis
dbfilename dump.rdb
appendfilename "appendonly.aof"
```

### 10. Security ✅

**Current:** No authentication
**Target:** ACL + TLS

```bash
# redis.conf
# Enable authentication
requirepass your_redis_password_here

# Enable TLS (for production)
tls-port 6379
tls-cert-file /path/to/redis.crt
tls-key-file /path/to/redis.key
tls-ca-cert-file /path/to/ca.crt

# Disable dangerous commands
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command CONFIG ""
```

---

## Implementation Tasks

### Phase 1: Immediate (Story 2.6 Post-Mortem)

- [ ] Add connection pooling to CacheStrategy
- [ ] Implement health check endpoint
- [ ] Add Prometheus metrics
- [ ] Configure explicit timeouts

### Phase 2: Short-term (Before Epic 3)

- [ ] Implement circuit breaker pattern
- [ ] Add retry logic with exponential backoff
- [ ] Enable Redis persistence (RDB + AOF)
- [ ] Add Redis to infrastructure monitoring

### Phase 3: Long-term (Production Readiness)

- [ ] Enable Redis authentication (ACL)
- [ ] Configure TLS for production
- [ ] Set up Redis Sentinel for HA
- [ ] Document failover procedures

---

## Testing

### Unit Tests

```python
# tests/test_cache_strategy.py
@pytest.mark.asyncio
async def test_redis_health_check():
    """Test Redis health check."""
    cache = CacheStrategy()
    is_healthy = await cache.health_check()
    assert is_healthy is True

@pytest.mark.asyncio
async def test_redis_retry_on_failure():
    """Test retry logic on Redis failure."""
    cache = CacheStrategy()

    with patch.object(cache._redis, 'get', side_effect=RedisError):
        result = await cache.get("test_key")
        assert result is None  # Should return None after retries
```

### Load Tests

```python
# tests/test_redis_load.py
@pytest.mark.asyncio
async def test_redis_concurrent_connections():
    """Test connection pool under load."""
    cache = CacheStrategy()

    tasks = [cache.get(f"key_{i}") for i in range(100)]
    results = await asyncio.gather(*tasks)

    assert all(r is None for r in results)  # Cache misses expected
    # No connection pool exhaustion errors
```

---

## Monitoring

### Prometheus Metrics to Track

```
# Request metrics
redis_get_requests_total{status="hit|miss|error"}
redis_set_requests_total{status="success|error"}

# Latency metrics
redis_get_latency_seconds
redis_set_latency_seconds

# Connection pool metrics
redis_connection_pool_active_connections
redis_connection_pool_idle_connections

# Circuit breaker metrics
redis_circuit_breaker_state{state="closed|open|half_open"}
redis_circuit_breaker_failures_total
```

### Grafana Dashboard Queries

```promql
# Redis hit rate
rate(redis_get_requests_total{status="hit"}[5m]) /
rate(redis_get_requests_total[5m])

# Redis latency P95
histogram_quantile(0.95, rate(redis_get_latency_seconds_bucket[5m]))

# Circuit breaker trips
redis_circuit_breaker_state{state="open"}
```

---

## Success Criteria

- ✅ Connection pooling configured (max_connections)
- ✅ Health check endpoint returns 200 OK
- ✅ Circuit breaker prevents cascade failures
- ✅ Prometheus metrics exported
- ✅ Retry logic with exponential backoff
- ✅ Graceful degradation on Redis failure
- ✅ All unit and load tests pass
- ✅ Redis persistence enabled (RDB + AOF)

---

## Next Steps

1. **Implement connection pooling** in CacheStrategy
2. **Add health check** to /health endpoint
3. **Configure Prometheus metrics** for Redis operations
4. **Enable circuit breaker** for Redis failures
5. **Document failover procedures** for operations
6. **Add Redis to production infrastructure** checklist

---

*Prepared for: Epic 3 preparation*
*Owner: Charlie (Senior Dev)*
*Priority: Medium (Redis is now critical path)*
