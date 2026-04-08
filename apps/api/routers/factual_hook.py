"""Factual hook verification endpoint for manual testing and Script Lab integration."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_session as get_db
from dependencies.org_context import get_current_org_id
from middleware.namespace_guard import verify_namespace_access
from schemas.factual_hook import (
    FactualHookVerifyRequest,
    FactualVerificationResponse,
    ClaimVerificationResponse,
)
from services.factual_hook import FactualHookService
from services.llm.service import LLMService
from services.llm.providers.factory import create_llm_provider
from services.embedding.service import EmbeddingService
from services.embedding.providers.factory import create_embedding_provider
from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter()


async def _build_services(session: AsyncSession):
    llm_provider = create_llm_provider(settings)
    llm_service = LLMService(llm_provider)
    embedding_provider = create_embedding_provider(settings)
    embedding_service = EmbeddingService(embedding_provider)
    return llm_service, embedding_service


@router.post("/verify", response_model=FactualVerificationResponse)
async def verify_response(
    body: FactualHookVerifyRequest,
    org_id: str = Depends(get_current_org_id),
    session: AsyncSession = Depends(get_db),
    _ns: str = Depends(verify_namespace_access),
):
    if not settings.FACTUAL_HOOK_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "factual_hook_disabled",
                "message": "Factual hook is disabled",
            },
        )

    kb_ids = None
    if body.agent_id is not None:
        result = await session.execute(
            text(
                "SELECT knowledge_base_ids FROM agents "
                "WHERE id = :aid AND org_id = :org_id AND soft_delete = false"
            ),
            {"aid": body.agent_id, "org_id": org_id},
        )
        row = result.fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "agent_not_found", "message": "Agent not found"},
            )
        kb_ids = row[0]

    llm_service, embedding_service = await _build_services(session)
    hook = FactualHookService(session, llm_service, embedding_service)
    hook_result = await hook.verify_and_correct(
        response=body.response_text,
        source_chunks=[],
        query="manual-verification",
        org_id=org_id,
        knowledge_base_ids=kb_ids,
    )

    return FactualVerificationResponse(
        was_corrected=hook_result.was_corrected,
        correction_count=hook_result.correction_count,
        verified_claims=[
            ClaimVerificationResponse(
                claim_text=vc.claim_text,
                is_supported=vc.is_supported,
                max_similarity=vc.max_similarity,
                verification_error=vc.verification_error,
            )
            for vc in hook_result.verified_claims
        ],
        verification_timed_out=hook_result.verification_timed_out,
    )
