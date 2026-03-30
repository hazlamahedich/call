import logging
from fastapi import APIRouter, HTTPException, Request, status, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from pydantic import ValidationError as PydanticValidationError

from database.session import get_session, set_tenant_context
from models.agent import Agent
from models.script import Script
from schemas.onboarding import OnboardingPayload
from services.base import TenantService

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])
logger = logging.getLogger(__name__)

_agent_service = TenantService[Agent](Agent)
_script_service = TenantService[Script](Script)


@router.post("/complete")
async def complete_onboarding(
    request: Request,
    payload: OnboardingPayload,
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
        OnboardingPayload.model_validate(payload.model_dump())
    except PydanticValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "ONBOARDING_VALIDATION_ERROR",
                "message": "Invalid onboarding payload",
                "errors": e.errors(),
            },
        )

    await set_tenant_context(session, org_id)

    existing = await _agent_service.list_all(session, limit=1)
    complete_agents = [a for a in existing if a.onboarding_complete]
    if complete_agents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "ONBOARDING_ALREADY_COMPLETE",
                "message": "Onboarding has already been completed for this organization",
            },
        )

    try:
        agent = Agent(
            name="My First Agent",
            voice_id=payload.voice_id,
            business_goal=payload.business_goal,
            safety_level=payload.safety_level,
            integration_type=payload.integration_type,
            onboarding_complete=True,
        )
        agent = await _agent_service.create(session, agent)

        script = Script(
            agent_id=agent.id,
            name="Initial Script",
            content="",
            version=1,
            script_context=payload.script_context,
        )
        script = await _script_service.create(session, script)

        await session.commit()

        return {
            "agent": agent.model_dump(by_alias=True),
            "script": script.model_dump(by_alias=True),
        }
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Onboarding creation failed for org {org_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "ONBOARDING_CREATE_ERROR",
                "message": "Failed to create onboarding records",
            },
        )


@router.get("/status")
async def get_onboarding_status(
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

    await set_tenant_context(session, org_id)

    result = await session.execute(
        text("SELECT id FROM agents WHERE onboarding_complete = true LIMIT 1")
    )
    row = result.first()

    return {"completed": row is not None}
