import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_session
from middleware.vapi_auth import verify_vapi_signature
from schemas.call import VapiWebhookPayload
from services.vapi import handle_call_started, handle_call_ended, handle_call_failed
from services.transcription import (
    handle_transcript_event,
    handle_speech_start,
    handle_speech_end,
)

router = APIRouter(prefix="/webhooks/vapi", tags=["Vapi Webhooks"])
logger = logging.getLogger(__name__)


@router.post("/call-events", dependencies=[Depends(verify_vapi_signature)])
async def handle_call_events(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    try:
        raw = await request.json()
    except Exception:
        logger.warning(
            "Vapi webhook received non-JSON body",
            extra={"code": "VAPI_WEBHOOK_INVALID_BODY"},
        )
        return {"received": True}

    try:
        body = VapiWebhookPayload.model_validate(raw)
    except Exception:
        logger.warning(
            "Vapi webhook payload validation failed",
            extra={"code": "VAPI_WEBHOOK_VALIDATION_FAILED"},
        )
        return {"received": True}

    message = body.message or {}
    event_type = message.get("type", "")
    call_data = message.get("call") or {}
    vapi_call_id = call_data.get("id", "") if isinstance(call_data, dict) else ""

    logger.info(
        "Vapi webhook event received",
        extra={"event_type": event_type, "vapi_call_id": vapi_call_id},
    )

    if not vapi_call_id:
        logger.warning(
            "Vapi webhook missing call_id",
            extra={"code": "VAPI_WEBHOOK_MISSING_CALL_ID", "event_type": event_type},
        )
        return {"received": True}

    metadata = message.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}
    org_id = metadata.get("org_id", "")

    if not org_id:
        logger.warning(
            "Vapi webhook missing org_id — cannot route to tenant",
            extra={
                "code": "VAPI_WEBHOOK_MISSING_ORG_ID",
                "vapi_call_id": vapi_call_id,
                "event_type": event_type,
            },
        )
        return {"received": True}

    phone_number = ""
    if isinstance(call_data, dict):
        phone_number = call_data.get(
            "phoneNumber", call_data.get("customer", {}).get("number", "")
        )
        if not phone_number:
            logger.info(
                "Vapi webhook has no phone_number — may be externally triggered call",
                extra={
                    "code": "VAPI_WEBHOOK_NO_PHONE",
                    "vapi_call_id": vapi_call_id,
                    "event_type": event_type,
                },
            )

    try:
        if event_type == "call-start":
            await handle_call_started(
                session,
                vapi_call_id,
                org_id,
                metadata=metadata,
                phone_number=phone_number,
            )
        elif event_type == "call-end":
            duration = (
                call_data.get("duration") if isinstance(call_data, dict) else None
            )
            recording_url = (
                call_data.get("recordingUrl") if isinstance(call_data, dict) else None
            )
            await handle_call_ended(
                session,
                vapi_call_id,
                org_id=org_id,
                duration=int(duration) if duration is not None else None,
                recording_url=recording_url,
            )
        elif event_type == "call-failed":
            error_msg = (
                call_data.get("error", {}) if isinstance(call_data, dict) else {}
            )
            if isinstance(error_msg, dict):
                error_str = error_msg.get("message", str(error_msg))
            else:
                error_str = str(error_msg)
            await handle_call_failed(
                session, vapi_call_id, org_id=org_id, error_message=error_str
            )
        elif event_type == "transcript":
            transcript_data = message.get("transcript", {})
            await handle_transcript_event(
                session,
                vapi_call_id,
                org_id,
                transcript_data={"transcript": transcript_data, **message},
            )
        elif event_type == "speech-start":
            speech_data = message.get("speech", {})
            if not isinstance(speech_data, dict):
                speech_data = {}
            speech_data.setdefault("speaker", message.get("speaker", "lead"))
            await handle_speech_start(session, vapi_call_id, org_id, speech_data)
        elif event_type == "speech-end":
            speech_data = message.get("speech", {})
            if not isinstance(speech_data, dict):
                speech_data = {}
            speech_data.setdefault("speaker", message.get("speaker", "lead"))
            await handle_speech_end(session, vapi_call_id, org_id, speech_data)
        else:
            logger.info(
                "Unhandled Vapi event type",
                extra={"event_type": event_type, "vapi_call_id": vapi_call_id},
            )
    except Exception as e:
        logger.error(
            "Error processing Vapi webhook",
            extra={
                "code": "VAPI_WEBHOOK_HANDLER_ERROR",
                "event_type": event_type,
                "vapi_call_id": vapi_call_id,
                "error": str(e),
            },
        )

    return {"received": True}
