"""Script generation API endpoints.

Provides grounded response generation and agent-level grounding configuration.
"""

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_session as get_db
from dependencies.org_context import get_current_org_id
from middleware.namespace_guard import verify_namespace_access
from models.agent import Agent
from schemas.script_generation import (
    ScriptConfigRequest,
    ScriptConfigResponse,
    ScriptGenerateRequest,
    ScriptGenerateResponse,
    SourceChunkInfo,
)
from services.embedding import EmbeddingService, create_embedding_provider
from services.grounding import GroundingService
from services.knowledge_search import search_knowledge_chunks
from services.llm.providers.factory import create_llm_provider
from services.llm.service import LLMService
from services.script_generation import (
    NO_KNOWLEDGE_FALLBACK,
    AgentNotFoundError,
    AgentOwnershipError,
    ScriptGenerationService,
)
from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Scripts"])

_embedding_service: EmbeddingService | None = None


def _get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        provider = create_embedding_provider(settings)
        _embedding_service = EmbeddingService(provider=provider)
    return _embedding_service


async def _set_rls_context(session: AsyncSession, org_id: str):
    await session.execute(
        text("SELECT set_config('app.current_org_id', :org_id, false)"),
        {"org_id": org_id},
    )


async def _load_and_validate_agent(
    session: AsyncSession, agent_id: int, org_id: str
) -> Agent:
    agent = await session.execute(
        select(Agent).where(
            Agent.id == agent_id,
            Agent.soft_delete == False,  # noqa: E712
        )
    )
    agent_obj = agent.scalar_one_or_none()
    if agent_obj is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent_obj.org_id != org_id:
        raise HTTPException(
            status_code=403,
            detail="Agent belongs to different organization",
        )
    return agent_obj


def _parse_grounding_config(agent: Agent) -> dict | None:
    if agent.grounding_config:
        return agent.grounding_config
    return None


@router.post("/generate", response_model=ScriptGenerateResponse)
async def generate_script_response(
    request_body: ScriptGenerateRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
    org_id: str = Depends(get_current_org_id),
):
    org_id = await verify_namespace_access(session=session, org_id=org_id)
    await _set_rls_context(session, org_id)

    agent = None
    grounding_config = None
    config_version = None
    if request_body.agent_id is not None:
        agent = await _load_and_validate_agent(session, request_body.agent_id, org_id)
        grounding_config = _parse_grounding_config(agent)
        config_version = agent.config_version

    mode = (
        request_body.override_grounding_mode
        or (grounding_config and grounding_config.get("groundingMode"))
        or settings.GROUNDING_DEFAULT_MODE
    )
    max_chunks = (
        request_body.override_max_chunks
        or (grounding_config and grounding_config.get("maxSourceChunks"))
        or settings.GROUNDING_MAX_SOURCE_CHUNKS
    )
    min_confidence = (
        grounding_config and grounding_config.get("minConfidence")
    ) or settings.GROUNDING_MIN_CONFIDENCE
    system_prompt_template = agent.system_prompt_template if agent else None

    llm_provider = create_llm_provider(settings)
    llm_service = LLMService(llm_provider)
    embedding_service = _get_embedding_service()

    service = ScriptGenerationService(
        llm_service=llm_service,
        embedding_service=embedding_service,
        session=session,
        redis_client=None,
    )

    result = await service.generate_response(
        query=request_body.query,
        org_id=org_id,
        agent_id=request_body.agent_id,
        grounding_mode=mode,
        max_source_chunks=max_chunks,
        system_prompt_template=system_prompt_template,
        min_confidence=min_confidence,
    )

    source_chunk_infos = [
        SourceChunkInfo(
            chunk_id=c["chunk_id"],
            knowledge_base_id=c["knowledge_base_id"],
            similarity=round(c["similarity"], 4),
        )
        for c in result.source_chunks
    ]

    return ScriptGenerateResponse(
        response=result.response,
        grounding_confidence=result.grounding_confidence,
        is_low_confidence=result.is_low_confidence,
        source_chunks=source_chunk_infos,
        model=result.model,
        latency_ms=result.latency_ms,
        grounding_mode=result.grounding_mode,
        was_truncated=result.was_truncated,
        cached=result.cached,
        config_version=config_version,
    )


@router.post("/config", response_model=ScriptConfigResponse)
async def configure_script(
    request_body: ScriptConfigRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
    org_id: str = Depends(get_current_org_id),
):
    org_id = await verify_namespace_access(session=session, org_id=org_id)
    await _set_rls_context(session, org_id)

    agent = await _load_and_validate_agent(session, request_body.agent_id, org_id)

    if agent.config_version != request_body.expected_version:
        raise HTTPException(
            status_code=409,
            detail=f"Config was modified. Current version: {agent.config_version}",
        )

    new_config = {
        "groundingMode": request_body.grounding_mode,
        "maxSourceChunks": request_body.max_source_chunks,
        "minConfidence": request_body.min_confidence,
    }

    agent.grounding_config = new_config
    if request_body.system_prompt_template is not None:
        agent.system_prompt_template = request_body.system_prompt_template
    agent.config_version += 1

    session.add(agent)
    await session.flush()

    logger.info(
        "Grounding config updated for agent %d",
        request_body.agent_id,
        extra={
            "org_id": org_id,
            "agent_id": request_body.agent_id,
            "new_version": agent.config_version,
            "grounding_mode": request_body.grounding_mode,
        },
    )

    return ScriptConfigResponse(
        agent_id=agent.id,
        grounding_mode=request_body.grounding_mode,
        max_source_chunks=request_body.max_source_chunks,
        min_confidence=request_body.min_confidence,
        system_prompt_template=agent.system_prompt_template,
        config_version=agent.config_version,
    )


@router.get("/config/{agent_id}", response_model=ScriptConfigResponse)
async def get_script_config(
    agent_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db),
    org_id: str = Depends(get_current_org_id),
):
    org_id = await verify_namespace_access(session=session, org_id=org_id)
    await _set_rls_context(session, org_id)

    agent = await _load_and_validate_agent(session, agent_id, org_id)

    config = agent.grounding_config or {}
    return ScriptConfigResponse(
        agent_id=agent.id,
        grounding_mode=config.get("groundingMode", settings.GROUNDING_DEFAULT_MODE),
        max_source_chunks=config.get(
            "maxSourceChunks", settings.GROUNDING_MAX_SOURCE_CHUNKS
        ),
        min_confidence=config.get("minConfidence", settings.GROUNDING_MIN_CONFIDENCE),
        system_prompt_template=agent.system_prompt_template,
        config_version=agent.config_version,
    )
