"""Shared query helpers for loading entities with ownership validation and RLS context.

Eliminates dual query paths (router ORM vs service raw SQL) by providing
a single canonical set of loaders used by both routers and services.
"""

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from models.agent import Agent
from models.lead import Lead
from models.script import Script


async def set_rls_context(session: AsyncSession, org_id: str):
    """Set RLS tenant context for the current transaction.

    Uses is_local=True (transaction-scoped, NOT session-scoped) per Story 3.3 learning.
    """
    await session.execute(
        text("SELECT set_config('app.current_org_id', :org_id, true)"),
        {"org_id": org_id},
    )


async def load_agent_for_context(
    session: AsyncSession, agent_id: int, org_id: str, for_update: bool = False
) -> Agent:
    query = select(Agent).where(
        Agent.id == agent_id,
        Agent.soft_delete == False,  # noqa: E712
    )
    if for_update:
        query = query.with_for_update()
    result = await session.execute(query)
    obj = result.scalar_one_or_none()
    if obj is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "agent_not_found", "message": "Agent not found"},
        )
    if obj.org_id != org_id:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "wrong_org",
                "message": "Agent belongs to different organization",
            },
        )
    return obj


async def load_lead_for_context(
    session: AsyncSession, lead_id: int, org_id: str, for_update: bool = False
) -> Lead:
    query = select(Lead).where(
        Lead.id == lead_id,
        Lead.soft_delete == False,  # noqa: E712
    )
    if for_update:
        query = query.with_for_update()
    result = await session.execute(query)
    obj = result.scalar_one_or_none()
    if obj is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "lead_not_found",
                "message": f"Lead with ID {lead_id} not found",
            },
        )
    if obj.org_id != org_id:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "wrong_org",
                "message": "Lead belongs to different organization",
            },
        )
    return obj


async def load_script_for_context(
    session: AsyncSession, script_id: int, org_id: str
) -> Script:
    result = await session.execute(
        select(Script).where(
            Script.id == script_id,
            Script.soft_delete == False,  # noqa: E712
        )
    )
    obj = result.scalar_one_or_none()
    if obj is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "script_not_found", "message": "Script not found"},
        )
    if obj.org_id != org_id:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "wrong_org",
                "message": "Script belongs to different organization",
            },
        )
    return obj
