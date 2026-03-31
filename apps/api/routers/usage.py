import logging

from fastapi import APIRouter, HTTPException, Request, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from pydantic import ValidationError as PydanticValidationError

from database.session import get_session
from middleware.usage_guard import check_call_cap
from schemas.usage import UsageRecordPayload, UsageSummaryResponse
from services.usage import (
    record_usage,
    get_usage_summary,
    check_usage_cap,
    get_monthly_usage,
    get_monthly_cap,
    get_org_plan,
)

router = APIRouter(prefix="/usage", tags=["Usage"])
logger = logging.getLogger(__name__)


@router.get("/summary", response_model=UsageSummaryResponse)
async def get_summary(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    org_id = getattr(request.state, "org_id", None)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "AUTH_FORBIDDEN",
                "message": "Organization context required",
            },
        )

    try:
        summary = await get_usage_summary(session, org_id)
        return UsageSummaryResponse(**summary)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Usage summary failed for org {org_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "USAGE_INTERNAL_ERROR",
                "message": "Failed to retrieve usage summary",
            },
        )


@router.post(
    "/record",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(check_call_cap)],
)
async def record(
    request: Request,
    payload: UsageRecordPayload,
    session: AsyncSession = Depends(get_session),
):
    org_id = getattr(request.state, "org_id", None)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "AUTH_FORBIDDEN",
                "message": "Organization context required",
            },
        )

    try:
        log = await record_usage(
            session,
            org_id,
            resource_type=payload.resource_type,
            resource_id=payload.resource_id,
            action=payload.action,
            metadata=payload.metadata or "{}",
        )
        serialized = log.model_dump(by_alias=True)
        return {"usageLog": serialized}
    except PydanticValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "USAGE_INVALID_RESOURCE",
                "message": str(e.errors()),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Usage recording failed for org {org_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "USAGE_INTERNAL_ERROR",
                "message": "Failed to record usage event",
            },
        )


@router.get("/check")
async def check(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    org_id = getattr(request.state, "org_id", None)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "AUTH_FORBIDDEN",
                "message": "Organization context required",
            },
        )

    try:
        plan = await get_org_plan(session, org_id)
        threshold = await check_usage_cap(session, org_id, plan=plan)
        used = await get_monthly_usage(session, org_id)
        cap = await get_monthly_cap(session, org_id, plan=plan)
        return {"threshold": threshold, "used": used, "cap": cap}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Usage check failed for org {org_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "USAGE_INTERNAL_ERROR",
                "message": "Failed to check usage cap",
            },
        )
