from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

import redis.asyncio as aioredis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from database.session import set_tenant_context
from models.dnc_check_log import DncCheckLog
from models.lead import Lead
from .blocklist import check_tenant_blocklist, add_to_blocklist
from .circuit_breaker import DncCircuitBreaker
from .dnc_com_provider import DncComProvider
from .dnc_provider import DncCheckResult, DncScrubSummary, validate_e164
from .exceptions import ComplianceBlockError

logger = logging.getLogger(__name__)

_circuit_breaker = DncCircuitBreaker()
_provider: Optional[DncComProvider] = None
_provider_lock = asyncio.Lock()

_SCRUB_CONCURRENCY = 10

_RETRY_BACKOFF_TOTAL_SECS = 7.5

_RELEASE_LOCK_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


def _get_provider() -> DncComProvider:
    global _provider
    if _provider is None:
        _provider = DncComProvider()
    return _provider


async def close_provider() -> None:
    global _provider
    async with _provider_lock:
        if _provider is not None:
            await _provider.close()
            _provider = None


def _mask_phone(phone: str) -> str:
    if len(phone) <= 4:
        return "***"
    return phone[:3] + "***" + phone[-2:]


def _cache_key(org_id: str, phone_number: str) -> str:
    return f"dnc:{org_id}:{phone_number}"


def _lock_key(org_id: str, phone_number: str) -> str:
    return f"dnc:lock:{org_id}:{phone_number}"


async def _read_cache(redis_client: aioredis.Redis | None, key: str) -> Optional[dict]:
    if redis_client is None:
        return None
    try:
        raw = await redis_client.get(key)
        if raw:
            return json.loads(raw)
    except Exception as e:
        logger.warning(
            "Redis cache read failed, falling through",
            extra={"code": "DNC_CACHE_READ_ERROR", "error": str(e)},
        )
    return None


async def _write_cache(
    redis_client: aioredis.Redis | None,
    key: str,
    value: dict,
    ttl_seconds: int,
) -> None:
    if redis_client is None:
        return
    try:
        await redis_client.setex(key, ttl_seconds, json.dumps(value))
    except Exception as e:
        logger.warning(
            "Redis cache write failed",
            extra={"code": "DNC_CACHE_WRITE_ERROR", "error": str(e)},
        )


async def _log_check(
    session: AsyncSession,
    phone_number: str,
    check_type: str,
    source: str,
    result: str,
    org_id: str,
    response_time_ms: int,
    lead_id: Optional[int] = None,
    campaign_id: Optional[int] = None,
    call_id: Optional[int] = None,
    raw_response: Optional[dict] = None,
) -> None:
    try:
        nested = await session.begin_nested()
        await set_tenant_context(session, org_id)
        log = DncCheckLog.model_validate(
            {
                "phoneNumber": phone_number,
                "checkType": check_type,
                "source": source,
                "result": result,
                "leadId": lead_id,
                "campaignId": campaign_id,
                "callId": call_id,
                "responseTimeMs": response_time_ms,
                "rawResponse": json.dumps(raw_response) if raw_response else None,
            }
        )
        log.org_id = org_id
        session.add(log)
        await nested.commit()
    except Exception as e:
        logger.error(
            "Failed to log DNC check",
            extra={"code": "DNC_LOG_ERROR", "error": str(e)},
        )


def _log_latency(elapsed_ms: int, phone_number: str) -> None:
    masked = _mask_phone(phone_number)
    if elapsed_ms > settings.DNC_PRE_DIAL_SLOW_THRESHOLD_MS:
        logger.warning(
            "DNC pre-dial check slow",
            extra={
                "code": "DNC_SLOW_CHECK",
                "latency_ms": elapsed_ms,
                "phone_masked": masked,
            },
        )
    if elapsed_ms > 500:
        logger.critical(
            "DNC pre-dial check critically slow",
            extra={
                "code": "DNC_CRITICAL_SLOW",
                "latency_ms": elapsed_ms,
                "phone_masked": masked,
            },
        )


async def check_dnc_realtime(
    session: AsyncSession,
    phone_number: str,
    org_id: str,
    redis_client: aioredis.Redis | None = None,
    lead_id: Optional[int] = None,
    campaign_id: Optional[int] = None,
    call_id: Optional[int] = None,
    check_type: str = "pre_dial",
    fail_closed: bool = True,
) -> DncCheckResult:
    start = time.monotonic()

    try:
        phone_number = validate_e164(phone_number)
    except ValueError as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        await _log_check(
            session,
            phone_number or "",
            check_type,
            "validation",
            "error",
            org_id,
            elapsed_ms,
            lead_id=lead_id,
            campaign_id=campaign_id,
            call_id=call_id,
            raw_response={"error": str(exc)},
        )
        raise ComplianceBlockError(
            code="DNC_INVALID_PHONE_FORMAT",
            phone_number=phone_number or "",
            call_id=call_id,
            source="validation",
        )

    if not await _circuit_breaker.is_available(org_id, redis_client):
        elapsed_ms = int((time.monotonic() - start) * 1000)
        await _log_check(
            session,
            phone_number,
            check_type,
            "circuit_breaker",
            "error",
            org_id,
            elapsed_ms,
            lead_id=lead_id,
            campaign_id=campaign_id,
            call_id=call_id,
        )
        if fail_closed:
            raise ComplianceBlockError(
                code="DNC_PROVIDER_UNAVAILABLE",
                phone_number=phone_number,
                call_id=call_id,
                source="circuit_breaker",
            )
        return DncCheckResult(
            phone_number=phone_number,
            is_blocked=False,
            source="circuit_breaker",
            result="error",
            response_time_ms=elapsed_ms,
        )

    lock_owner = str(uuid.uuid4())
    lock_ttl = int(_RETRY_BACKOFF_TOTAL_SECS) + 5
    lock_acquired = False
    lk = _lock_key(org_id, phone_number)

    if redis_client is not None:
        try:
            lock_acquired = await redis_client.set(lk, lock_owner, nx=True, ex=lock_ttl)
        except (aioredis.RedisError, OSError):
            lock_acquired = False

    try:
        cache_hit = await _read_cache(redis_client, _cache_key(org_id, phone_number))
        if cache_hit:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            result_val = cache_hit.get("result", "clear")
            await _log_check(
                session,
                phone_number,
                check_type,
                "cache",
                result_val,
                org_id,
                elapsed_ms,
                lead_id=lead_id,
                campaign_id=campaign_id,
                call_id=call_id,
            )
            _log_latency(elapsed_ms, phone_number)
            return DncCheckResult(
                phone_number=phone_number,
                is_blocked=(result_val == "blocked"),
                source=cache_hit.get("source", "cache"),
                result=result_val,
                response_time_ms=elapsed_ms,
            )

        bl_entry = await check_tenant_blocklist(session, phone_number, org_id)
        if bl_entry:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            await _write_cache(
                redis_client,
                _cache_key(org_id, phone_number),
                {
                    "result": "blocked",
                    "source": bl_entry.source,
                    "checked_at": datetime.now(timezone.utc).isoformat(),
                },
                settings.DNC_CACHE_BLOCKED_TTL_SECONDS,
            )
            await _log_check(
                session,
                phone_number,
                check_type,
                bl_entry.source,
                "blocked",
                org_id,
                elapsed_ms,
                lead_id=lead_id,
                campaign_id=campaign_id,
                call_id=call_id,
            )
            _log_latency(elapsed_ms, phone_number)
            return DncCheckResult(
                phone_number=phone_number,
                is_blocked=True,
                source=bl_entry.source,
                result="blocked",
                response_time_ms=elapsed_ms,
            )

        provider = _get_provider()
        sla_timeout = (
            settings.DNC_PRE_DIAL_TIMEOUT_MS / 1000.0
            if check_type == "pre_dial"
            else None
        )
        if sla_timeout is not None:
            try:
                provider_result = await asyncio.wait_for(
                    provider.lookup(phone_number),
                    timeout=sla_timeout,
                )
            except asyncio.TimeoutError:
                elapsed_ms = int((time.monotonic() - start) * 1000)
                await _circuit_breaker.record_failure(org_id, redis_client)
                await _log_check(
                    session,
                    phone_number,
                    check_type,
                    "provider_timeout",
                    "error",
                    org_id,
                    elapsed_ms,
                    lead_id=lead_id,
                    campaign_id=campaign_id,
                    call_id=call_id,
                    raw_response={
                        "error": "sla_timeout",
                        "sla_ms": settings.DNC_PRE_DIAL_TIMEOUT_MS,
                    },
                )
                if fail_closed:
                    raise ComplianceBlockError(
                        code="DNC_PROVIDER_UNAVAILABLE",
                        phone_number=phone_number,
                        call_id=call_id,
                        source="provider_timeout",
                        retry_after_seconds=60,
                    )
                return DncCheckResult(
                    phone_number=phone_number,
                    is_blocked=False,
                    source="provider_timeout",
                    result="error",
                    response_time_ms=elapsed_ms,
                )
        else:
            provider_result = await provider.lookup(phone_number)
        elapsed_ms = provider_result.response_time_ms or int(
            (time.monotonic() - start) * 1000
        )

        if provider_result.result == "error":
            await _circuit_breaker.record_failure(org_id, redis_client)
            await _log_check(
                session,
                phone_number,
                check_type,
                provider_result.source,
                "error",
                org_id,
                elapsed_ms,
                lead_id=lead_id,
                campaign_id=campaign_id,
                call_id=call_id,
                raw_response=provider_result.raw_response,
            )
            if fail_closed:
                raise ComplianceBlockError(
                    code="DNC_PROVIDER_UNAVAILABLE",
                    phone_number=phone_number,
                    call_id=call_id,
                    source="dnc_provider_error",
                    retry_after_seconds=60,
                )
            return provider_result

        await _circuit_breaker.record_success(org_id, redis_client)

        ttl = (
            settings.DNC_CACHE_BLOCKED_TTL_SECONDS
            if provider_result.is_blocked
            else settings.DNC_CACHE_CLEAR_TTL_SECONDS
        )
        await _write_cache(
            redis_client,
            _cache_key(org_id, phone_number),
            {
                "result": provider_result.result,
                "source": provider_result.source,
                "checked_at": datetime.now(timezone.utc).isoformat(),
            },
            ttl,
        )

        await _log_check(
            session,
            phone_number,
            check_type,
            provider_result.source,
            provider_result.result,
            org_id,
            elapsed_ms,
            lead_id=lead_id,
            campaign_id=campaign_id,
            call_id=call_id,
            raw_response=provider_result.raw_response,
        )

        _log_latency(elapsed_ms, phone_number)

        provider_result.response_time_ms = elapsed_ms
        return provider_result

    except ComplianceBlockError:
        raise
    except Exception as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        await _circuit_breaker.record_failure(org_id, redis_client)
        await _log_check(
            session,
            phone_number,
            check_type,
            "provider_error",
            "error",
            org_id,
            elapsed_ms,
            lead_id=lead_id,
            campaign_id=campaign_id,
            call_id=call_id,
            raw_response={"error": str(exc)},
        )
        if fail_closed:
            raise ComplianceBlockError(
                code="DNC_PROVIDER_UNAVAILABLE",
                phone_number=phone_number,
                call_id=call_id,
                source="provider_error",
                retry_after_seconds=60,
            )
        raise

    finally:
        if lock_acquired and redis_client is not None:
            try:
                await redis_client.eval(
                    _RELEASE_LOCK_SCRIPT,
                    1,
                    lk,
                    lock_owner,
                )
            except Exception:
                pass


def _normalize_source(source: str) -> str:
    known = {"national_dnc", "state_dnc", "tenant_blocklist"}
    if source in known:
        return source
    if "state" in source.lower():
        return "state_dnc"
    if "blocklist" in source.lower():
        return "tenant_blocklist"
    return "national_dnc"


async def scrub_leads_batch(
    session: AsyncSession,
    org_id: str,
    lead_ids: list[int],
    redis_client: aioredis.Redis | None = None,
    campaign_id: Optional[int] = None,
) -> DncScrubSummary:
    summary = DncScrubSummary(total=len(lead_ids))
    seen_phones: set[str] = set()
    skipped = 0
    semaphore = asyncio.Semaphore(_SCRUB_CONCURRENCY)

    async def _scrub_one(lead_id: int, phone: str) -> None:
        async with semaphore:
            try:
                check_result = await check_dnc_realtime(
                    session,
                    phone,
                    org_id,
                    redis_client,
                    lead_id=lead_id,
                    campaign_id=campaign_id,
                    check_type="upload_scrub",
                    fail_closed=False,
                )

                if check_result.is_blocked:
                    summary.blocked += 1
                    src = _normalize_source(check_result.source)
                    summary.sources[src] += 1
                    await session.execute(
                        text(
                            "UPDATE leads SET status = 'dnc_blocked' WHERE id = :lid AND org_id = :oid"
                        ),
                        {"lid": lead_id, "oid": org_id},
                    )
                    try:
                        await add_to_blocklist(
                            session,
                            org_id,
                            phone,
                            src,
                            lead_id=lead_id,
                        )
                    except Exception:
                        pass
                elif check_result.result == "error":
                    summary.unchecked += 1
                    await session.execute(
                        text(
                            "UPDATE leads SET status = 'dnc_pending' WHERE id = :lid AND org_id = :oid"
                        ),
                        {"lid": lead_id, "oid": org_id},
                    )

            except ComplianceBlockError:
                summary.unchecked += 1
                await session.execute(
                    text(
                        "UPDATE leads SET status = 'dnc_pending' WHERE id = :lid AND org_id = :oid"
                    ),
                    {"lid": lead_id, "oid": org_id},
                )
            except Exception as e:
                logger.warning(
                    "Batch scrub error for lead",
                    extra={
                        "code": "DNC_BATCH_ERROR",
                        "lead_id": lead_id,
                        "error": str(e),
                    },
                )
                summary.unchecked += 1
                await session.execute(
                    text(
                        "UPDATE leads SET status = 'dnc_pending' WHERE id = :lid AND org_id = :oid"
                    ),
                    {"lid": lead_id, "oid": org_id},
                )

    for i in range(0, len(lead_ids), settings.DNC_BATCH_SIZE):
        batch_ids = lead_ids[i : i + settings.DNC_BATCH_SIZE]
        placeholders = ",".join(f":lid{j}" for j in range(len(batch_ids)))
        params: dict = {f"lid{j}": bid for j, bid in enumerate(batch_ids)}
        params["org_id"] = org_id

        await set_tenant_context(session, org_id)
        result = await session.execute(
            text(
                f"SELECT id, phone FROM leads "
                f"WHERE id IN ({placeholders}) AND org_id = :org_id AND phone IS NOT NULL"
            ),
            params,
        )
        rows = result.fetchall()

        tasks: list[asyncio.Task] = []
        for row in rows:
            lead_id = row[0]
            phone = row[1]
            if not phone:
                skipped += 1
                continue
            if phone in seen_phones:
                skipped += 1
                continue
            seen_phones.add(phone)
            tasks.append(asyncio.create_task(_scrub_one(lead_id, phone)))

        if tasks:
            await asyncio.gather(*tasks)
        await session.flush()

    summary.skipped = skipped
    return summary
