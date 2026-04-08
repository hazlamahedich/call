import logging
from functools import lru_cache

from fastapi import APIRouter, Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_session as get_db
from dependencies.org_context import get_current_org_id
from middleware.namespace_guard import verify_namespace_access
from schemas.script_lab import (
    CreateLabSessionRequest,
    LabSessionResponse,
    LabChatRequest,
    LabChatResponse,
    ScenarioOverlayRequest,
    SessionSourcesResponse,
)
from services.script_lab import ScriptLabService
from services.embedding import EmbeddingService, create_embedding_provider
from services.llm.providers.factory import create_llm_provider
from services.llm.service import LLMService
from services.shared_queries import set_rls_context
from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Script Lab"])


@lru_cache(maxsize=1)
def _get_llm_service() -> LLMService:
    provider = create_llm_provider(settings)
    return LLMService(provider)


@lru_cache(maxsize=1)
def _get_embedding_service() -> EmbeddingService:
    provider = create_embedding_provider(settings)
    return EmbeddingService(provider=provider)


async def _get_redis(request: Request) -> Redis | None:
    return request.app.state.redis if hasattr(request.app.state, "redis") else None


@router.post("/sessions", response_model=LabSessionResponse)
async def create_session(
    body: CreateLabSessionRequest,
    session: AsyncSession = Depends(get_db),
    org_id: str = Depends(get_current_org_id),
):
    org_id = await verify_namespace_access(session=session, org_id=org_id)
    await set_rls_context(session, org_id)

    service = ScriptLabService(session)
    return await service.create_session(
        org_id=org_id,
        agent_id=body.agent_id,
        script_id=body.script_id,
        lead_id=body.lead_id,
    )


@router.post("/sessions/{session_id}/chat", response_model=LabChatResponse)
async def send_chat(
    session_id: int,
    body: LabChatRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
    org_id: str = Depends(get_current_org_id),
):
    org_id = await verify_namespace_access(session=session, org_id=org_id)
    await set_rls_context(session, org_id)

    llm_service = _get_llm_service()
    embedding_service = _get_embedding_service()
    redis_client = await _get_redis(request)

    service = ScriptLabService(session)
    return await service.send_chat_message(
        org_id=org_id,
        session_id=session_id,
        message=body.message,
        llm_service=llm_service,
        embedding_service=embedding_service,
        redis_client=redis_client,
    )


@router.post(
    "/sessions/{session_id}/scenario-overlay", response_model=LabSessionResponse
)
async def set_overlay(
    session_id: int,
    body: ScenarioOverlayRequest,
    session: AsyncSession = Depends(get_db),
    org_id: str = Depends(get_current_org_id),
):
    org_id = await verify_namespace_access(session=session, org_id=org_id)
    await set_rls_context(session, org_id)

    service = ScriptLabService(session)
    return await service.set_scenario_overlay(
        org_id=org_id,
        session_id=session_id,
        overlay=body.overlay,
    )


@router.get("/sessions/{session_id}/sources", response_model=SessionSourcesResponse)
async def get_sources(
    session_id: int,
    session: AsyncSession = Depends(get_db),
    org_id: str = Depends(get_current_org_id),
):
    org_id = await verify_namespace_access(session=session, org_id=org_id)
    await set_rls_context(session, org_id)

    service = ScriptLabService(session)
    sources = await service.get_session_sources(
        org_id=org_id,
        session_id=session_id,
    )
    return SessionSourcesResponse(
        session_id=session_id,
        total_turns=len(sources),
        sources=sources,
    )


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: int,
    session: AsyncSession = Depends(get_db),
    org_id: str = Depends(get_current_org_id),
):
    org_id = await verify_namespace_access(session=session, org_id=org_id)
    await set_rls_context(session, org_id)

    service = ScriptLabService(session)
    await service.delete_session(org_id=org_id, session_id=session_id)
    return {"status": "deleted"}
