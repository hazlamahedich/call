import logging

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_session, set_tenant_context
from services.usage import check_usage_cap

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
        threshold = await check_usage_cap(session, org_id)
    except Exception as e:
        # DELIBERATE DESIGN DECISION: fail-open on DB errors.
        # If the database is unavailable, we allow requests through rather than
        # blocking all tenants. This trades potential overages for availability.
        # Revenue risk is bounded by the time window of the DB outage.
        # Revisit if SLA requirements change to prefer deny-on-error.
        logger.error(f"Usage guard DB check failed for org {org_id}: {e}")
        return
    if threshold == "exceeded":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "USAGE_LIMIT_EXCEEDED",
                "message": "Monthly call limit has been reached. Upgrade your plan or wait for the next billing cycle.",
            },
        )
