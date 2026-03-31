from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import set_tenant_context
from models.transcript import TranscriptEntry
from models.voice_event import VoiceEvent
from services.ws_manager import manager as ws_manager

logger = logging.getLogger(__name__)


def _row_to_transcript_entry(row) -> TranscriptEntry:
    if hasattr(row, "_mapping"):
        m = row._mapping
    else:
        m = row
    return TranscriptEntry.model_construct(
        id=m["id"],
        org_id=m["org_id"],
        call_id=m["call_id"],
        vapi_call_id=m["vapi_call_id"],
        role=m["role"],
        text=m["text"],
        start_time=m["start_time"],
        end_time=m["end_time"],
        confidence=m["confidence"],
        words_json=m["words_json"],
        received_at=m["received_at"],
        vapi_event_timestamp=m["vapi_event_timestamp"],
        created_at=m["created_at"],
        updated_at=m["updated_at"],
        soft_delete=m["soft_delete"],
    )


def _row_to_voice_event(row) -> VoiceEvent:
    if hasattr(row, "_mapping"):
        m = row._mapping
    else:
        m = row
    return VoiceEvent.model_construct(
        id=m["id"],
        org_id=m["org_id"],
        call_id=m["call_id"],
        vapi_call_id=m["vapi_call_id"],
        event_type=m["event_type"],
        speaker=m["speaker"],
        event_metadata=m["event_metadata"],
        received_at=m["received_at"],
        vapi_event_timestamp=m["vapi_event_timestamp"],
        created_at=m["created_at"],
        updated_at=m["updated_at"],
        soft_delete=m["soft_delete"],
    )


def _map_role(vapi_role: str) -> str:
    mapping = {
        "assistant": "assistant-ai",
        "ai": "assistant-ai",
        "user": "lead",
        "human": "assistant-human",
    }
    return mapping.get(vapi_role.lower(), "lead")


def _compute_latency(
    received_at: datetime, vapi_event_timestamp: Optional[float]
) -> Optional[float]:
    if vapi_event_timestamp is None:
        return None
    try:
        vapi_dt = datetime.fromtimestamp(vapi_event_timestamp, tz=timezone.utc)
        delta = received_at - vapi_dt
        return delta.total_seconds() * 1000
    except (OSError, ValueError, OverflowError):
        return None


async def _resolve_call_id(
    session: AsyncSession, vapi_call_id: str, org_id: str
) -> Optional[int]:
    result = await session.execute(
        text("SELECT id FROM calls WHERE vapi_call_id = :vci AND org_id = :org_id"),
        {"vci": vapi_call_id, "org_id": org_id},
    )
    row = result.first()
    if row:
        return row[0]
    return None


async def _detect_interruption(
    session: AsyncSession,
    vapi_call_id: str,
    org_id: str,
    current_speaker: str,
) -> bool:
    if current_speaker != "lead":
        return False
    result = await session.execute(
        text(
            "SELECT event_type, speaker FROM voice_events "
            "WHERE vapi_call_id = :vci AND org_id = :org_id "
            "AND event_type IN ('speech_start', 'speech_end') "
            "ORDER BY received_at DESC LIMIT 1"
        ),
        {"vci": vapi_call_id, "org_id": org_id},
    )
    last_event = result.first()
    if last_event and last_event[0] == "speech_start" and last_event[1] == "ai":
        return True
    return False


async def handle_transcript_event(
    session: AsyncSession,
    vapi_call_id: str,
    org_id: str,
    transcript_data: dict,
) -> TranscriptEntry:
    await set_tenant_context(session, org_id)

    call_id = await _resolve_call_id(session, vapi_call_id, org_id)
    if call_id is None:
        logger.warning(
            "Transcript event received but call not found",
            extra={
                "code": "TRANSCRIPT_PROCESSING_ERROR",
                "vapi_call_id": vapi_call_id,
            },
        )

    transcript_obj = transcript_data.get("transcript", transcript_data)
    vapi_role = transcript_obj.get("role", "user")
    role = _map_role(vapi_role)
    entry_text = transcript_obj.get("text", "")
    words = transcript_obj.get("words", [])
    words_json = json.dumps(words) if words else None

    start_time = None
    end_time = None
    confidence = None
    if words:
        starts = [w.get("start", 0) for w in words if w.get("start") is not None]
        ends = [w.get("end", 0) for w in words if w.get("end") is not None]
        confidences = [
            w.get("confidence") for w in words if w.get("confidence") is not None
        ]
        if starts:
            start_time = min(starts)
        if ends:
            end_time = max(ends)
        if confidences:
            confidence = sum(confidences) / len(confidences)

    vapi_event_timestamp = transcript_data.get("timestamp")
    received_at = datetime.now(timezone.utc)

    result = await session.execute(
        text(
            "INSERT INTO transcript_entries "
            "(org_id, call_id, vapi_call_id, role, text, start_time, end_time, "
            "confidence, words_json, received_at, vapi_event_timestamp, created_at, updated_at) "
            "VALUES (:org_id, :call_id, :vci, :role, :text, :start_time, :end_time, "
            ":confidence, :words_json, :received_at, :vapi_ts, NOW(), NOW()) "
            "RETURNING id, org_id, call_id, vapi_call_id, role, text, start_time, end_time, "
            "confidence, words_json, received_at, vapi_event_timestamp, "
            "created_at, updated_at, soft_delete"
        ),
        {
            "org_id": org_id,
            "call_id": call_id,
            "vci": vapi_call_id,
            "role": role,
            "text": entry_text,
            "start_time": start_time,
            "end_time": end_time,
            "confidence": confidence,
            "words_json": words_json,
            "received_at": received_at,
            "vapi_ts": vapi_event_timestamp,
        },
    )
    row = result.first()
    entry = _row_to_transcript_entry(row)

    latency_ms = _compute_latency(received_at, vapi_event_timestamp)
    if latency_ms is not None:
        logger.info(
            "Transcript event processed",
            extra={
                "code": "TRANSCRIPT_EVENT_PROCESSED",
                "vapi_call_id": vapi_call_id,
                "transit_latency_ms": round(latency_ms, 2),
            },
        )
    else:
        logger.info(
            "Transcript event processed",
            extra={
                "code": "TRANSCRIPT_EVENT_PROCESSED",
                "vapi_call_id": vapi_call_id,
            },
        )

    if entry.call_id:
        try:
            import asyncio

            entry_dict = {
                "id": entry.id,
                "callId": entry.call_id,
                "role": entry.role,
                "text": entry.text,
                "startTime": entry.start_time,
                "endTime": entry.end_time,
                "confidence": entry.confidence,
                "receivedAt": entry.received_at.isoformat()
                if entry.received_at
                else None,
            }
            asyncio.create_task(
                ws_manager.broadcast_to_call(
                    entry.call_id,
                    {"type": "transcript", "entry": entry_dict},
                )
            )
        except Exception:
            pass

    return entry


async def handle_speech_start(
    session: AsyncSession,
    vapi_call_id: str,
    org_id: str,
    speech_data: dict,
) -> VoiceEvent:
    await set_tenant_context(session, org_id)

    call_id = await _resolve_call_id(session, vapi_call_id, org_id)
    speaker = speech_data.get("speaker", "lead")
    if isinstance(speaker, str):
        speaker = speaker.lower()
    speaker = "ai" if speaker in ("assistant", "ai") else "lead"

    vapi_event_timestamp = speech_data.get("timestamp")
    received_at = datetime.now(timezone.utc)

    is_interruption = await _detect_interruption(session, vapi_call_id, org_id, speaker)
    if is_interruption:
        await session.execute(
            text(
                "INSERT INTO voice_events "
                "(org_id, call_id, vapi_call_id, event_type, speaker, received_at, "
                "vapi_event_timestamp, created_at, updated_at) "
                "VALUES (:org_id, :call_id, :vci, 'interruption', :speaker, :received_at, "
                ":vapi_ts, NOW(), NOW())"
            ),
            {
                "org_id": org_id,
                "call_id": call_id,
                "vci": vapi_call_id,
                "speaker": speaker,
                "received_at": received_at,
                "vapi_ts": vapi_event_timestamp,
            },
        )
        logger.info(
            "Interruption detected",
            extra={
                "code": "INTERRUPTION_DETECTED",
                "vapi_call_id": vapi_call_id,
                "speaker": speaker,
            },
        )

    result = await session.execute(
        text(
            "INSERT INTO voice_events "
            "(org_id, call_id, vapi_call_id, event_type, speaker, received_at, "
            "vapi_event_timestamp, created_at, updated_at) "
            "VALUES (:org_id, :call_id, :vci, 'speech_start', :speaker, :received_at, "
            ":vapi_ts, NOW(), NOW()) "
            "RETURNING id, org_id, call_id, vapi_call_id, event_type, speaker, "
            "event_metadata, received_at, vapi_event_timestamp, "
            "created_at, updated_at, soft_delete"
        ),
        {
            "org_id": org_id,
            "call_id": call_id,
            "vci": vapi_call_id,
            "speaker": speaker,
            "received_at": received_at,
            "vapi_ts": vapi_event_timestamp,
        },
    )
    row = result.first()
    event = _row_to_voice_event(row)

    logger.info(
        "Speech start event processed",
        extra={
            "code": "SPEECH_EVENT_PROCESSED",
            "vapi_call_id": vapi_call_id,
            "speaker": speaker,
        },
    )

    return event


async def handle_speech_end(
    session: AsyncSession,
    vapi_call_id: str,
    org_id: str,
    speech_data: dict,
) -> VoiceEvent:
    await set_tenant_context(session, org_id)

    call_id = await _resolve_call_id(session, vapi_call_id, org_id)
    speaker = speech_data.get("speaker", "lead")
    if isinstance(speaker, str):
        speaker = speaker.lower()
    speaker = "ai" if speaker in ("assistant", "ai") else "lead"

    vapi_event_timestamp = speech_data.get("timestamp")
    received_at = datetime.now(timezone.utc)

    result = await session.execute(
        text(
            "INSERT INTO voice_events "
            "(org_id, call_id, vapi_call_id, event_type, speaker, received_at, "
            "vapi_event_timestamp, created_at, updated_at) "
            "VALUES (:org_id, :call_id, :vci, 'speech_end', :speaker, :received_at, "
            ":vapi_ts, NOW(), NOW()) "
            "RETURNING id, org_id, call_id, vapi_call_id, event_type, speaker, "
            "event_metadata, received_at, vapi_event_timestamp, "
            "created_at, updated_at, soft_delete"
        ),
        {
            "org_id": org_id,
            "call_id": call_id,
            "vci": vapi_call_id,
            "speaker": speaker,
            "received_at": received_at,
            "vapi_ts": vapi_event_timestamp,
        },
    )
    row = result.first()
    event = _row_to_voice_event(row)

    logger.info(
        "Speech end event processed",
        extra={
            "code": "SPEECH_EVENT_PROCESSED",
            "vapi_call_id": vapi_call_id,
            "speaker": speaker,
        },
    )

    return event
