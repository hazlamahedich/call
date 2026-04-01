from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import set_tenant_context
from models.call import Call
from services.base import TenantService
from services.usage import record_usage
from services.vapi_client import initiate_call

logger = logging.getLogger(__name__)

_call_service = TenantService[Call](Call)


def _row_to_call(row) -> Call:
    if hasattr(row, "_mapping"):
        m = row._mapping
    else:
        m = row
    return Call.model_construct(
        id=m["id"],
        org_id=m["org_id"],
        vapi_call_id=m["vapi_call_id"],
        lead_id=m["lead_id"],
        agent_id=m["agent_id"],
        campaign_id=m["campaign_id"],
        status=m["status"],
        duration=m["duration"],
        recording_url=m["recording_url"],
        phone_number=m["phone_number"],
        transcript=m["transcript"],
        ended_at=m["ended_at"],
        created_at=m["created_at"],
        updated_at=m["updated_at"],
        soft_delete=m["soft_delete"],
    )


def _safe_int(value) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


async def trigger_outbound_call(
    session: AsyncSession,
    org_id: str,
    phone_number: str,
    lead_id: Optional[int] = None,
    agent_id: Optional[int] = None,
    campaign_id: Optional[int] = None,
    assistant_id: Optional[str] = None,
) -> Call:
    await set_tenant_context(session, org_id)

    if not assistant_id:
        raise ValueError("VAPI_NOT_CONFIGURED: No assistant_id provided")

    placeholder_id = str(uuid.uuid4())
    call = Call.model_validate(
        {
            "vapiCallId": placeholder_id,
            "phoneNumber": phone_number,
            "leadId": lead_id,
            "agentId": agent_id,
            "campaignId": campaign_id,
            "status": "pending",
        }
    )
    call = await _call_service.create(session, call)
    await session.flush()

    try:
        metadata = {"org_id": org_id}
        if lead_id:
            metadata["lead_id"] = str(lead_id)
        if agent_id:
            metadata["agent_id"] = str(agent_id)

        result = await initiate_call(
            phone_number=phone_number,
            assistant_id=assistant_id,
            metadata=metadata,
        )
        vapi_call_id = result.get("id", "")

        await session.execute(
            text("UPDATE calls SET vapi_call_id = :vci WHERE id = :cid"),
            {"vci": vapi_call_id, "cid": call.id},
        )
        call.vapi_call_id = vapi_call_id
    except Exception:
        await session.execute(
            text(
                "UPDATE calls SET status = 'failed', vapi_call_id = :fallback WHERE id = :cid"
            ),
            {"fallback": f"_failed_{call.id}", "cid": call.id},
        )
        call.status = "failed"
        raise

    await record_usage(
        session,
        org_id,
        resource_type="call",
        resource_id=str(call.id),
        action="call_initiated",
    )

    return call


async def handle_call_started(
    session: AsyncSession,
    vapi_call_id: str,
    org_id: str,
    metadata: Optional[dict] = None,
    phone_number: str = "",
) -> Call:
    await set_tenant_context(session, org_id)

    metadata = metadata or {}
    lead_id = _safe_int(metadata.get("lead_id"))
    agent_id = _safe_int(metadata.get("agent_id"))

    result = await session.execute(
        text(
            "INSERT INTO calls (org_id, vapi_call_id, lead_id, agent_id, status, phone_number, created_at, updated_at) "
            "VALUES (:org_id, :vci, :lead_id, :agent_id, 'in_progress', :phone, NOW(), NOW()) "
            "ON CONFLICT (vapi_call_id) DO UPDATE SET status = 'in_progress', updated_at = NOW() "
            "RETURNING id, org_id, vapi_call_id, lead_id, agent_id, campaign_id, "
            "status, duration, recording_url, phone_number, transcript, ended_at, "
            "created_at, updated_at, soft_delete"
        ),
        {
            "org_id": org_id,
            "vci": vapi_call_id,
            "lead_id": lead_id,
            "agent_id": agent_id,
            "phone": phone_number,
        },
    )
    row = result.first()
    return _row_to_call(row)


async def handle_call_ended(
    session: AsyncSession,
    vapi_call_id: str,
    org_id: str,
    duration: Optional[int] = None,
    recording_url: Optional[str] = None,
) -> Call:
    await set_tenant_context(session, org_id)

    result = await session.execute(
        text(
            "UPDATE calls SET status = 'completed', duration = :dur, "
            "recording_url = :rec_url, ended_at = :ended_at, updated_at = NOW() "
            "WHERE vapi_call_id = :vci AND status != 'completed' "
            "RETURNING id, org_id, vapi_call_id, lead_id, agent_id, campaign_id, "
            "status, duration, recording_url, phone_number, transcript, ended_at, "
            "created_at, updated_at, soft_delete"
        ),
        {
            "dur": duration,
            "rec_url": recording_url,
            "ended_at": datetime.now(timezone.utc),
            "vci": vapi_call_id,
        },
    )
    row = result.first()
    if not row:
        existing = await session.execute(
            text("SELECT * FROM calls WHERE vapi_call_id = :vci"),
            {"vci": vapi_call_id},
        )
        row = existing.first()
        if not row:
            raise ValueError(f"Call not found for vapi_call_id: {vapi_call_id}")

    call = _row_to_call(row)

    if call.id:
        try:
            te_result = await session.execute(
                text(
                    "SELECT role, text FROM transcript_entries "
                    "WHERE call_id = :cid AND org_id = :org_id "
                    "ORDER BY start_time ASC, id ASC"
                ),
                {"cid": call.id, "org_id": call.org_id},
            )
            entries = te_result.fetchall()
            if entries:
                role_prefixes = {
                    "assistant-ai": "[AI]",
                    "assistant-human": "[Human]",
                    "lead": "[Lead]",
                }
                lines = []
                for entry in entries:
                    prefix = role_prefixes.get(entry[0], "[Unknown]")
                    lines.append(f"{prefix}: {entry[1]}")
                transcript_text = "\n".join(lines)
                await session.execute(
                    text("UPDATE calls SET transcript = :transcript WHERE id = :cid"),
                    {"transcript": transcript_text, "cid": call.id},
                )
                call.transcript = transcript_text
        except Exception as e:
            logger.error(
                "Transcript aggregation error",
                extra={
                    "code": "TRANSCRIPT_AGGREGATION_ERROR",
                    "call_id": call.id,
                    "error": str(e),
                },
            )

    return call


async def handle_call_failed(
    session: AsyncSession,
    vapi_call_id: str,
    org_id: str,
    error_message: Optional[str] = None,
) -> Call:
    await set_tenant_context(session, org_id)

    result = await session.execute(
        text(
            "UPDATE calls SET status = 'failed', ended_at = :ended_at, "
            "transcript = COALESCE(transcript, :err_msg), "
            "updated_at = NOW() WHERE vapi_call_id = :vci AND status != 'failed' "
            "RETURNING id, org_id, vapi_call_id, lead_id, agent_id, campaign_id, "
            "status, duration, recording_url, phone_number, transcript, ended_at, "
            "created_at, updated_at, soft_delete"
        ),
        {
            "ended_at": datetime.now(timezone.utc),
            "err_msg": f"[error] {error_message}" if error_message else None,
            "vci": vapi_call_id,
        },
    )
    row = result.first()
    if not row:
        existing = await session.execute(
            text("SELECT * FROM calls WHERE vapi_call_id = :vci"),
            {"vci": vapi_call_id},
        )
        row = existing.first()
        if not row:
            raise ValueError(f"Call not found for vapi_call_id: {vapi_call_id}")

    return _row_to_call(row)
