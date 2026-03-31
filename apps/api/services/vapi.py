from __future__ import annotations

import logging
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

    call = Call.model_validate(
        {
            "vapiCallId": "",
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
            text("UPDATE calls SET status = 'failed' WHERE id = :cid"),
            {"cid": call.id},
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
) -> Call:
    await set_tenant_context(session, org_id)

    metadata = metadata or {}
    lead_id = metadata.get("lead_id")
    agent_id = metadata.get("agent_id")

    result = await session.execute(
        text("SELECT id FROM calls WHERE vapi_call_id = :vci"),
        {"vci": vapi_call_id},
    )
    existing = result.first()

    if existing:
        await session.execute(
            text(
                "UPDATE calls SET status = 'in_progress', updated_at = NOW() "
                "WHERE vapi_call_id = :vci"
            ),
            {"vci": vapi_call_id},
        )
        updated = await session.execute(
            text("SELECT * FROM calls WHERE vapi_call_id = :vci"),
            {"vci": vapi_call_id},
        )
        row = updated.first()
        call = Call.model_construct(
            id=row[0],
            org_id=row[1],
            vapi_call_id=row[2],
            lead_id=row[3],
            agent_id=row[4],
            campaign_id=row[5],
            status="in_progress",
            duration=row[7],
            recording_url=row[8],
            phone_number=row[9],
            transcript=row[10],
            ended_at=row[11],
            created_at=row[12],
            updated_at=row[13],
            soft_delete=row[14],
        )
    else:
        call = Call.model_validate(
            {
                "vapiCallId": vapi_call_id,
                "leadId": int(lead_id) if lead_id else None,
                "agentId": int(agent_id) if agent_id else None,
                "status": "in_progress",
                "phoneNumber": "",
            }
        )
        call = await _call_service.create(session, call)

    return call


async def handle_call_ended(
    session: AsyncSession,
    vapi_call_id: str,
    duration: Optional[int] = None,
    recording_url: Optional[str] = None,
) -> Call:
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

    return Call.model_construct(
        id=row[0],
        org_id=row[1],
        vapi_call_id=row[2],
        lead_id=row[3],
        agent_id=row[4],
        campaign_id=row[5],
        status=row[6],
        duration=row[7],
        recording_url=row[8],
        phone_number=row[9],
        transcript=row[10],
        ended_at=row[11],
        created_at=row[12],
        updated_at=row[13],
        soft_delete=row[14],
    )


async def handle_call_failed(
    session: AsyncSession,
    vapi_call_id: str,
    error_message: Optional[str] = None,
) -> Call:
    result = await session.execute(
        text(
            "UPDATE calls SET status = 'failed', ended_at = :ended_at, "
            "updated_at = NOW() WHERE vapi_call_id = :vci AND status != 'failed' "
            "RETURNING id, org_id, vapi_call_id, lead_id, agent_id, campaign_id, "
            "status, duration, recording_url, phone_number, transcript, ended_at, "
            "created_at, updated_at, soft_delete"
        ),
        {
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

    return Call.model_construct(
        id=row[0],
        org_id=row[1],
        vapi_call_id=row[2],
        lead_id=row[3],
        agent_id=row[4],
        campaign_id=row[5],
        status=row[6],
        duration=row[7],
        recording_url=row[8],
        phone_number=row[9],
        transcript=row[10],
        ended_at=row[11],
        created_at=row[12],
        updated_at=row[13],
        soft_delete=row[14],
    )
