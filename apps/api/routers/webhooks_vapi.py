import logging
from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_session
from middleware.vapi_auth import verify_vapi_signature
from services.vapi import handle_call_started, handle_call_ended, handle_call_failed

router = APIRouter(prefix="/webhooks/vapi", tags=["Vapi Webhooks"])
logger = logging.getLogger(__name__)


@router.post("/call-events", dependencies=[Depends(verify_vapi_signature)])
async def handle_call_events(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    body = await request.json()
    message = body.get("message", {})
    event_type = message.get("type", "")
    call_data = message.get("call", {})
    vapi_call_id = call_data.get("id", "") if call_data else ""

    logger.info(f"Received Vapi webhook event: {event_type} (call_id={vapi_call_id})")

    if not vapi_call_id:
        logger.warning(f"Vapi webhook missing call_id for event type: {event_type}")
        return {"received": True}

    metadata = message.get("metadata", {}) or {}
    org_id = metadata.get("org_id", "")

    if not org_id:
        logger.warning(
            f"Vapi webhook missing org_id in metadata for call {vapi_call_id}"
        )
        return {"received": True}

    try:
        if event_type == "call-start":
            await handle_call_started(session, vapi_call_id, org_id, metadata=metadata)
        elif event_type == "call-end":
            duration = message.get("call", {}).get("duration")
            recording_url = message.get("call", {}).get("recordingUrl")
            await handle_call_ended(
                session,
                vapi_call_id,
                duration=int(duration) if duration is not None else None,
                recording_url=recording_url,
            )
        elif event_type == "call-failed":
            error_msg = message.get("call", {}).get("error", {})
            if isinstance(error_msg, dict):
                error_str = error_msg.get("message", str(error_msg))
            else:
                error_str = str(error_msg)
            await handle_call_failed(session, vapi_call_id, error_message=error_str)
        else:
            logger.info(f"Unhandled Vapi event type: {event_type}")
    except Exception as e:
        logger.error(
            f"Error processing Vapi webhook {event_type} for call {vapi_call_id}: {e}"
        )

    return {"received": True}
