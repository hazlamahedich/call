"""Script generation API endpoints.

Provides grounded response generation and agent-level grounding configuration.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from redis.asyncio import Redis
from sqlalchemy import select, text
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
from schemas.variable_injection import (
    ScriptRenderRequest,
    ScriptRenderResponse,
    VariablePreviewRequest,
    VariablePreviewResponse,
)
from services.embedding import EmbeddingService, create_embedding_provider
from services.grounding import GroundingService
from services.llm.providers.factory import create_llm_provider
from services.llm.service import LLMService
from services.script_generation import (
    ScriptGenerationService,
)
from services.shared_queries import (
    set_rls_context,
    load_agent_for_context,
    load_lead_for_context,
    load_script_for_context,
)
from services.variable_injection import VariableInjectionService, classify_source
from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Scripts"])

_llm_service: LLMService | None = None
_embedding_service: EmbeddingService | None = None


def _get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        provider = create_llm_provider(settings)
        _llm_service = LLMService(provider)
    return _llm_service


def _get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        provider = create_embedding_provider(settings)
        _embedding_service = EmbeddingService(provider=provider)
    return _embedding_service


async def _get_redis(request: Request) -> Redis | None:
    redis = request.app.state.redis if hasattr(request.app.state, "redis") else None
    return redis


def _parse_grounding_config(agent: Agent) -> dict | None:
    if agent.grounding_config:
        return agent.grounding_config
    return None


def _resolve_min_confidence(grounding_config: dict | None) -> float:
    if grounding_config is not None and "minConfidence" in grounding_config:
        return grounding_config["minConfidence"]
    return settings.GROUNDING_MIN_CONFIDENCE


@router.post("/generate", response_model=ScriptGenerateResponse)
async def generate_script_response(
    request_body: ScriptGenerateRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
    org_id: str = Depends(get_current_org_id),
):
    org_id = await verify_namespace_access(session=session, org_id=org_id)
    await set_rls_context(session, org_id)

    agent = None
    grounding_config = None
    config_version = None
    if request_body.agent_id is not None:
        agent = await load_agent_for_context(session, request_body.agent_id, org_id)
        grounding_config = _parse_grounding_config(agent)
        config_version = agent.config_version

    mode = request_body.override_grounding_mode
    if mode is None and grounding_config:
        mode = grounding_config.get("groundingMode")
    mode = mode or settings.GROUNDING_DEFAULT_MODE

    max_chunks = request_body.override_max_chunks
    if max_chunks is None and grounding_config:
        mc = grounding_config.get("maxSourceChunks")
        if mc is not None:
            max_chunks = int(mc)
    max_chunks = (
        max_chunks if max_chunks is not None else settings.GROUNDING_MAX_SOURCE_CHUNKS
    )
    min_confidence = _resolve_min_confidence(grounding_config)
    system_prompt_template = agent.system_prompt_template if agent else None

    llm_service = _get_llm_service()
    embedding_service = _get_embedding_service()
    redis_client = await _get_redis(request)

    service = ScriptGenerationService(
        llm_service=llm_service,
        embedding_service=embedding_service,
        session=session,
        redis_client=redis_client,
    )

    result = await service.generate_response(
        query=request_body.query,
        org_id=org_id,
        agent_id=request_body.agent_id,
        grounding_mode=mode,
        max_source_chunks=max_chunks,
        system_prompt_template=system_prompt_template,
        min_confidence=min_confidence,
        lead_id=request_body.lead_id,
        script_id=request_body.script_id,
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


@router.post("/render", response_model=ScriptRenderResponse)
async def render_script(
    request_body: ScriptRenderRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
    org_id: str = Depends(get_current_org_id),
):
    org_id = await verify_namespace_access(session=session, org_id=org_id)
    await set_rls_context(session, org_id)

    script = await load_script_for_context(session, request_body.script_id, org_id)
    lead = await load_lead_for_context(session, request_body.lead_id, org_id)

    agent = None
    if request_body.agent_id is not None:
        agent = await load_agent_for_context(session, request_body.agent_id, org_id)

    injection_service = VariableInjectionService(session)
    result = await injection_service.render_template(
        template=script.content,
        lead=lead,
        agent=agent,
        custom_fallbacks=request_body.custom_fallbacks,
    )

    return ScriptRenderResponse(
        rendered_text=result.rendered_text,
        resolved_variables=result.resolved_variables,
        unresolved_variables=result.unresolved_variables,
        was_rendered=result.was_rendered,
    )


@router.post("/preview-variables", response_model=VariablePreviewResponse)
async def preview_variables(
    request_body: VariablePreviewRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
    org_id: str = Depends(get_current_org_id),
):
    org_id = await verify_namespace_access(session=session, org_id=org_id)
    await set_rls_context(session, org_id)

    injection_service = VariableInjectionService(session)
    variables = injection_service.extract_variables(request_body.template)

    var_names = [v.name for v in variables]
    var_sources = {v.name: v.source_type for v in variables}

    sample_lead = request_body.sample_data or {}
    render_result = await injection_service.render_template(
        template=request_body.template,
        lead=sample_lead,
    )

    return VariablePreviewResponse(
        variables=var_names,
        variable_sources=var_sources,
        preview=render_result.rendered_text,
    )


@router.post("/config", response_model=ScriptConfigResponse)
async def configure_script(
    request_body: ScriptConfigRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
    org_id: str = Depends(get_current_org_id),
):
    org_id = await verify_namespace_access(session=session, org_id=org_id)
    await set_rls_context(session, org_id)

    agent = await load_agent_for_context(
        session, request_body.agent_id, org_id, for_update=True
    )

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

    redis_client = await _get_redis(request)
    if redis_client:
        cache_service = ScriptGenerationService(
            llm_service=None,
            embedding_service=None,
            session=None,
            redis_client=redis_client,
        )
        await cache_service.invalidate_cache(org_id, request_body.agent_id)

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

    assert agent.id is not None

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
    await set_rls_context(session, org_id)

    agent = await load_agent_for_context(session, agent_id, org_id)

    assert agent.id is not None
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
