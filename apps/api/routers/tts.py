import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_session
from dependencies.org_context import get_current_org_id
from services.tts.factory import get_tts_orchestrator

router = APIRouter(prefix="/tts", tags=["TTS"])
logger = logging.getLogger(__name__)


@router.get("/providers/health")
async def get_providers_health(
    request: Request,
    org_id: str = Depends(get_current_org_id),
):
    orchestrator = await get_tts_orchestrator()
    health = await orchestrator.get_providers_health()
    return {"providers": health}


@router.get("/session/{call_id}/status")
async def get_session_status(
    call_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_org_id),
):
    result = await session.execute(
        text("SELECT vapi_call_id FROM calls WHERE id = :call_id AND org_id = :org_id"),
        {"call_id": call_id, "org_id": org_id},
    )
    row = result.first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CALL_NOT_FOUND", "message": "Call not found"},
        )

    vapi_call_id = row[0]
    if vapi_call_id is None:
        orchestrator_fallback = await get_tts_orchestrator()
        return {
            "callId": call_id,
            "activeProvider": orchestrator_fallback.get_session_provider(""),
            "latencyHistory": [],
            "p95LatencyMs": None,
            "requestCount": 0,
        }

    orchestrator = await get_tts_orchestrator()

    active_provider = orchestrator.get_session_provider(vapi_call_id)
    latency_history = orchestrator.get_session_latency_history(vapi_call_id)

    p95 = None
    if latency_history:
        sorted_latencies = sorted(latency_history)
        if len(sorted_latencies) >= 2:
            idx = max(0, int(len(sorted_latencies) * 0.95) - 1)
        else:
            idx = 0
        p95 = sorted_latencies[idx]

    return {
        "callId": call_id,
        "vapiCallId": vapi_call_id,
        "activeProvider": active_provider,
        "latencyHistory": latency_history,
        "p95LatencyMs": p95,
        "requestCount": len(latency_history),
    }
