from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from database.session import set_tenant_context
from models.usage_log import UsageLog
from services.base import TenantService

logger = logging.getLogger(__name__)

_usage_service = TenantService[UsageLog](UsageLog)


async def get_org_plan(session: AsyncSession, org_id: str) -> str:
    await set_tenant_context(session, org_id)
    result = await session.execute(
        text("SELECT plan FROM agencies WHERE org_id = :org_id LIMIT 1"),
        {"org_id": org_id},
    )
    row = result.scalar()
    if row and row in settings.PLAN_CALL_CAPS:
        return row
    return "free"


async def get_tenant_cap_override(session: AsyncSession, org_id: str) -> Optional[int]:
    await set_tenant_context(session, org_id)
    result = await session.execute(
        text("SELECT monthly_call_cap FROM agencies WHERE org_id = :org_id LIMIT 1"),
        {"org_id": org_id},
    )
    row = result.scalar()
    return row if row and row > 0 else None


async def get_monthly_cap(
    session: AsyncSession, org_id: str, plan: str | None = None
) -> int:
    tenant_override = await get_tenant_cap_override(session, org_id)
    if tenant_override is not None:
        return tenant_override
    effective_plan = plan or "free"
    return settings.PLAN_CALL_CAPS.get(
        effective_plan, settings.DEFAULT_MONTHLY_CALL_CAP
    )


async def record_usage(
    session: AsyncSession,
    org_id: str,
    resource_type: str,
    resource_id: str,
    action: str,
    metadata: str = "{}",
) -> UsageLog:
    await set_tenant_context(session, org_id)
    try:
        parsed_metadata = json.loads(metadata) if metadata else {}
    except json.JSONDecodeError:
        parsed_metadata = {}
    log = UsageLog.model_validate(
        {
            "resourceType": resource_type,
            "resourceId": resource_id,
            "action": action,
            "metadataJson": parsed_metadata,
        }
    )
    return await _usage_service.create(session, log)


async def get_monthly_usage(session: AsyncSession, org_id: str) -> int:
    await set_tenant_context(session, org_id)
    result = await session.execute(
        text(
            """
            SELECT COUNT(*) FROM usage_logs
            WHERE action = 'call_initiated'
              AND org_id = :org_id
              AND created_at >= date_trunc('month', CURRENT_DATE)
            """
        ),
        {"org_id": org_id},
    )
    row = result.scalar()
    return row if row is not None else 0


async def get_monthly_usage_locked(session: AsyncSession, org_id: str) -> int:
    await set_tenant_context(session, org_id)
    result = await session.execute(
        text(
            """
            SELECT COUNT(*) FROM (
                SELECT 1 FROM usage_logs
                WHERE action = 'call_initiated'
                  AND org_id = :org_id
                  AND created_at >= date_trunc('month', CURRENT_DATE)
                FOR UPDATE
            ) sub
            """
        ),
        {"org_id": org_id},
    )
    row = result.scalar()
    return row if row is not None else 0


async def get_usage_summary(session: AsyncSession, org_id: str) -> dict:
    await set_tenant_context(session, org_id)
    plan = await get_org_plan(session, org_id)
    used = await get_monthly_usage(session, org_id)
    cap = await get_monthly_cap(session, org_id, plan=plan)
    percentage = round((used / cap) * 100, 2) if cap > 0 else 0.0
    threshold = _compute_threshold(used, cap)
    return {
        "used": used,
        "cap": cap,
        "percentage": percentage,
        "plan": plan,
        "threshold": threshold,
    }


def _compute_threshold(used: int, cap: int) -> str:
    if cap <= 0:
        return "exceeded"
    percentage = (used / cap) * 100
    if percentage >= 100:
        return "exceeded"
    if percentage >= 95:
        return "critical"
    if percentage >= 80:
        return "warning"
    return "ok"


async def check_usage_cap(
    session: AsyncSession,
    org_id: str,
    plan: str | None = None,
) -> str:
    await set_tenant_context(session, org_id)
    effective_plan = plan or await get_org_plan(session, org_id)
    used = await get_monthly_usage(session, org_id)
    cap = await get_monthly_cap(session, org_id, plan=effective_plan)
    return _compute_threshold(used, cap)


async def check_usage_cap_locked(
    session: AsyncSession,
    org_id: str,
    plan: str | None = None,
) -> str:
    await set_tenant_context(session, org_id)
    effective_plan = plan or await get_org_plan(session, org_id)
    used = await get_monthly_usage_locked(session, org_id)
    cap = await get_monthly_cap(session, org_id, plan=effective_plan)
    return _compute_threshold(used, cap)


async def check_and_increment_usage_atomic(
    session: AsyncSession,
    org_id: str,
    plan: str | None = None,
) -> tuple[str, int]:
    """
    Atomically check usage cap and increment usage counter.

    This function performs an atomic check-and-increment operation to prevent
    race conditions where concurrent requests could bypass the cap check.

    Returns:
        tuple: (threshold, new_usage_count)
            - threshold: "ok", "warning", "critical", or "exceeded"
            - new_usage_count: The usage count after the increment

    Raises:
        HTTPException: If the cap would be exceeded by this increment

    Race Condition Fix:
        The original implementation checked the cap in one transaction and
        recorded usage in another, allowing concurrent requests to bypass
        the cap. This function uses SELECT FOR UPDATE to lock the rows
        during the check, then inserts the usage record within the same
        transaction if the check passes.
    """
    from models.usage_log import UsageLog

    await set_tenant_context(session, org_id)
    effective_plan = plan or await get_org_plan(session, org_id)
    cap = await get_monthly_cap(session, org_id, plan=effective_plan)

    # Lock the usage rows for this org to prevent concurrent increments
    result = await session.execute(
        text(
            """
            SELECT COUNT(*) FROM usage_logs
            WHERE action = 'call_initiated'
              AND org_id = :org_id
              AND created_at >= date_trunc('month', CURRENT_DATE)
            FOR UPDATE
            """
        ),
        {"org_id": org_id},
    )
    current_usage = result.scalar() or 0
    new_usage = current_usage + 1
    threshold = _compute_threshold(new_usage, cap)

    # If cap would be exceeded, raise exception before recording
    if threshold == "exceeded":
        raise HTTPException(
            status_code=403,
            detail={
                "code": "USAGE_LIMIT_EXCEEDED",
                "message": f"Monthly call limit of {cap} would be exceeded. "
                f"Current usage: {current_usage}/{cap}",
            },
        )

    # Record the usage within the same transaction
    log = UsageLog.model_validate(
        {
            "resourceType": "call",
            "resourceId": org_id,  # Using org_id as resource_id for org-level caps
            "action": "call_initiated",
            "metadataJson": {"recorded_via": "atomic_increment"},
        }
    )
    session.add(log)
    await session.flush()  # Ensure the insert is flushed before commit

    return threshold, new_usage
