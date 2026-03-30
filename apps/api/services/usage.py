from __future__ import annotations

from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from database.session import set_tenant_context
from models.usage_log import UsageLog
from services.base import TenantService

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


async def get_monthly_cap(org_id: str, plan: str | None = None) -> int:
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
    log = UsageLog(
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        metadata_json=metadata,
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


async def get_usage_summary(session: AsyncSession, org_id: str) -> dict:
    await set_tenant_context(session, org_id)
    plan = await get_org_plan(session, org_id)
    used = await get_monthly_usage(session, org_id)
    cap = await get_monthly_cap(org_id, plan=plan)
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
    session: AsyncSession, org_id: str, plan: str | None = None
) -> str:
    await set_tenant_context(session, org_id)
    effective_plan = plan or await get_org_plan(session, org_id)
    used = await get_monthly_usage(session, org_id)
    cap = await get_monthly_cap(org_id, plan=effective_plan)
    return _compute_threshold(used, cap)
