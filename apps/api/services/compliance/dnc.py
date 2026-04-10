from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

import redis.asyncio as redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from database.session import set_tenant_context
from models.dnc_check_log import DncCheckLog
from .blocklist import check_tenant_blocklist, add_to_blocklist
from .circuit_breaker import DncCircuitBreaker
from .dnc_com_provider import DncComProvider
from .dnc_provider import DncCheckResult, DncScrubSummary, validate_e164
from .exceptions import ComplianceBlockError

logger = logging.getLogger(__name__)

_circuit_breaker = DncCircuitBreaker()
_provider = DncComProvider()


def _cache_key(org_id: str, phone_number: str) -> str:
    return f"dnc:{org_id}:{phone_number}"


def _lock_key(org_id: str, phone_number: str) -> str:
    return f"dnc:lock:{org_id}:{phone_number}"


async def _read_cache(redis_client: redis.Redis | None, key: str) -> Optional[dict]:
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
    redis_client: redis.Redis | None,
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
        await session.flush()
    except Exception as e:
        logger.warning(
            "Failed to log DNC check",
            extra={"code": "DNC_LOG_ERROR", "error": str(e)},
        )


async def check_dnc_realtime(
    session: AsyncSession,
    phone_number: str,
    org_id: str,
    redis_client: redis.Redis | None = None,
    lead_id: Optional[int] = None,
    campaign_id: Optional[int] = None,
    call_id: Optional[int] = None,
) -> DncCheckResult:
    start = time.monotonic()

    phone_number = validate_e164(phone_number)

    if not await _circuit_breaker.is_available(org_id, redis_client):
        elapsed_ms = int((time.monotonic() - start) * 1000)
        await _log_check(
            session,
            phone_number,
            "pre_dial",
            "circuit_breaker",
            "blocked",
            org_id,
            elapsed_ms,
            lead_id=lead_id,
            campaign_id=campaign_id,
            call_id=call_id,
        )
        return DncCheckResult(
            phone_number=phone_number,
            is_blocked=True,
            source="circuit_breaker",
            result="blocked",
            response_time_ms=elapsed_ms,
        )

    lock_owner = str(uuid.uuid4())
    lock_ttl = max(5, int(settings.DNC_PRE_DIAL_TIMEOUT_MS / 1000) + 2)
    lock_acquired = False
    lk = _lock_key(org_id, phone_number)

    if redis_client is not None:
        try:
            lock_acquired = await redis_client.set(lk, lock_owner, nx=True, ex=lock_ttl)
        except Exception:
            lock_acquired = False

    try:
        cache_hit = await _read_cache(redis_client, _cache_key(org_id, phone_number))
        if cache_hit:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            result_val = cache_hit.get("result", "clear")
            await _log_check(
                session,
                phone_number,
                "pre_dial",
                "cache",
                result_val,
                org_id,
                elapsed_ms,
                lead_id=lead_id,
                campaign_id=campaign_id,
                call_id=call_id,
            )
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
                "pre_dial",
                bl_entry.source,
                "blocked",
                org_id,
                elapsed_ms,
                lead_id=lead_id,
                campaign_id=campaign_id,
                call_id=call_id,
            )
            return DncCheckResult(
                phone_number=phone_number,
                is_blocked=True,
                source=bl_entry.source,
                result="blocked",
                response_time_ms=elapsed_ms,
            )

        provider_result = await _provider.lookup(phone_number)
        elapsed_ms = int((time.monotonic() - start) * 1000)

        if provider_result.result == "error":
            await _circuit_breaker.record_failure(org_id, redis_client)
            if settings.DNC_FAIL_CLOSED_ENABLED:
                await _log_check(
                    session,
                    phone_number,
                    "pre_dial",
                    provider_result.source,
                    "error",
                    org_id,
                    elapsed_ms,
                    lead_id=lead_id,
                    campaign_id=campaign_id,
                    call_id=call_id,
                    raw_response=provider_result.raw_response,
                )
                raise ComplianceBlockError(
                    code="DNC_PROVIDER_UNAVAILABLE",
                    phone_number=phone_number,
                    call_id=call_id,
                    source="dnc_provider_error",
                    retry_after_seconds=60,
                )
            await _log_check(
                session,
                phone_number,
                "pre_dial",
                provider_result.source,
                "error",
                org_id,
                elapsed_ms,
                lead_id=lead_id,
                campaign_id=campaign_id,
                call_id=call_id,
                raw_response=provider_result.raw_response,
            )
            return DncCheckResult(
                phone_number=phone_number,
                is_blocked=False,
                source=provider_result.source,
                result="error",
                response_time_ms=elapsed_ms,
            )

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
            "pre_dial",
            provider_result.source,
            provider_result.result,
            org_id,
            elapsed_ms,
            lead_id=lead_id,
            campaign_id=campaign_id,
            call_id=call_id,
            raw_response=provider_result.raw_response,
        )

        if elapsed_ms > settings.DNC_PRE_DIAL_SLOW_THRESHOLD_MS:
            logger.warning(
                "DNC pre-dial check slow",
                extra={
                    "code": "DNC_SLOW_CHECK",
                    "latency_ms": elapsed_ms,
                    "phone": phone_number,
                },
            )
        if elapsed_ms > 500:
            logger.critical(
                "DNC pre-dial check critically slow",
                extra={
                    "code": "DNC_CRITICAL_SLOW",
                    "latency_ms": elapsed_ms,
                    "phone": phone_number,
                },
            )

        provider_result.response_time_ms = elapsed_ms
        return provider_result

    finally:
        if lock_acquired and redis_client is not None:
            try:
                current = await redis_client.get(lk)
                if current and (
                    current == lock_owner.encode() or current == lock_owner
                ):
                    await redis_client.delete(lk)
            except Exception:
                pass


async def scrub_leads_batch(
    session: AsyncSession,
    org_id: str,
    lead_ids: list[int],
    redis_client: redis.Redis | None = None,
    campaign_id: Optional[int] = None,
) -> DncScrubSummary:
    summary = DncScrubSummary(total=len(lead_ids))
    seen_phones: set[str] = set()

    for i in range(0, len(lead_ids), settings.DNC_BATCH_SIZE):
        batch_ids = lead_ids[i : i + settings.DNC_BATCH_SIZE]
        placeholders = ",".join(f":lid{j}" for j in range(len(batch_ids)))
        params = {f"lid{j}": bid for j, bid in enumerate(batch_ids)}
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

        for row in rows:
            lead_id = row[0]
            phone = row[1]
            if not phone or phone in seen_phones:
                continue
            seen_phones.add(phone)

            try:
                check_result = await check_dnc_realtime(
                    session,
                    phone,
                    org_id,
                    redis_client,
                    lead_id=lead_id,
                    campaign_id=campaign_id,
                )

                if check_result.is_blocked:
                    summary.blocked += 1
                    src = check_result.source
                    if src in ("national_dnc", "state_dnc", "tenant_blocklist"):
                        summary.sources[src] += 1
                    else:
                        summary.sources["national_dnc"] += 1
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
                            src or "national_dnc",
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
                summary.blocked += 1
                summary.sources["national_dnc"] += 1
                await session.execute(
                    text(
                        "UPDATE leads SET status = 'dnc_blocked' WHERE id = :lid AND org_id = :oid"
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

        await session.flush()

    return summary
