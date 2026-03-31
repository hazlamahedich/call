import logging

from fastapi import APIRouter, HTTPException, Request, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from pydantic import ValidationError as PydanticValidationError

from database.session import get_session, set_tenant_context
from middleware.usage_guard import check_call_cap
from models.agent import Agent
from schemas.call import TriggerCallPayload
from services.base import TenantService
from services.vapi import trigger_outbound_call

router = APIRouter(prefix="/calls", tags=["Calls"])
logger = logging.getLogger(__name__)

_agent_service = TenantService[Agent](Agent)


async def _resolve_assistant_id(session, org_id, agent_id):
    if not agent_id:
        return None
    await set_tenant_context(session, org_id)
    agent = await _agent_service.get_by_id(session, agent_id)
    if not agent or not agent.voice_id:
        return None
    return agent.voice_id


def _compliance_pre_check(phone_number):
    try:
        from packages.compliance import check_dnc_eligibility

        logger.warning(
            "packages/compliance check skipped - not yet implemented for %s",
            phone_number,
        )
    except ImportError:
        logger.warning(
            "packages/compliance not yet fully implemented - "
            "skipping DNC eligibility check for %s",
            phone_number,
        )
    except Exception as exc:
        logger.warning("Compliance check failed: %s", exc)


@router.post(
    "/trigger",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(check_call_cap)],
)
async def trigger_call(
    request: Request,
    payload: TriggerCallPayload,
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
        assistant_id = await _resolve_assistant_id(session, org_id, payload.agent_id)
        await _compliance_pre_check(payload.phone_number)

        call = await trigger_outbound_call(
            session,
            org_id,
            phone_number=payload.phone_number,
            lead_id=payload.lead_id,
            agent_id=payload.agent_id,
            campaign_id=payload.campaign_id,
            assistant_id=assistant_id,
        )

        return {"call": call.model_dump(by_alias=True)}
    except PydanticValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "VAPI_CALL_TRIGGER_FAILED",
                "message": str(e.errors()),
            },
        )
    except HTTPException:
        raise
    except ValueError as e:
        error_msg = str(e)
        code = (
            "VAPI_NOT_CONFIGURED"
            if "VAPI_NOT_CONFIGURED" in error_msg
            else "VAPI_CALL_TRIGGER_FAILED"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": code,
                "message": error_msg,
            },
        )
    except Exception as e:
        logger.error("Call trigger failed for org %s: %s", org_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "VAPI_CALL_TRIGGER_FAILED",
                "message": "Failed to trigger outbound call",
            },
        )
