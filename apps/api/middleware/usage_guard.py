import logging

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_session, set_tenant_context
from services.usage import check_and_increment_usage_atomic

logger = logging.getLogger(__name__)


async def check_call_cap(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    org_id = getattr(request.state, "org_id", None)
    if not org_id:
        return
    try:
        await set_tenant_context(session, org_id)
        await check_and_increment_usage_atomic(session, org_id)
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Usage guard atomic check failed for org {org_id}: {e}")
        return
