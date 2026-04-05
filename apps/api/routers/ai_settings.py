import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_session as get_db
from middleware.auth_middleware import auth_middleware
from models.ai_provider_settings import AIProviderSettings
from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["AI Provider Settings"])


PROVIDER_MODELS = {
    "openai": {
        "embedding": [
            "text-embedding-3-small",
            "text-embedding-3-large",
            "text-embedding-ada-002",
        ],
        "llm": ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
    },
    "gemini": {
        "embedding": ["gemini-embedding-001"],
        "llm": [
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        ],
    },
}


class AIProviderConfigResponse(BaseModel):
    provider: str
    embedding_model: str
    embedding_dimensions: int
    llm_model: str
    has_api_key: bool
    connection_status: str

    class Config:
        from_attributes = True


class AIProviderUpdatePayload(BaseModel):
    provider: str
    api_key: str
    embedding_model: Optional[str] = None
    llm_model: Optional[str] = None


class ConnectionTestResponse(BaseModel):
    success: bool
    message: str


@router.get("/settings/ai-provider", response_model=AIProviderConfigResponse)
async def get_ai_provider_config(
    session: AsyncSession = Depends(get_db),
    token=Depends(auth_middleware),
):
    org_id = token.org_id
    from services.tenant_helpers import set_tenant_context

    await set_tenant_context(session, org_id)

    config = AIProviderSettings.get_for_org(session, org_id)
    if not config:
        return AIProviderConfigResponse(
            provider=settings.AI_PROVIDER,
            embedding_model=settings.AI_EMBEDDING_MODEL,
            embedding_dimensions=settings.AI_EMBEDDING_DIMENSIONS,
            llm_model=settings.AI_LLM_MODEL,
            has_api_key=bool(settings.OPENAI_API_KEY or settings.GEMINI_API_KEY),
            connection_status="untested",
        )

    return AIProviderConfigResponse(
        provider=config.provider,
        embedding_model=config.embedding_model,
        embedding_dimensions=config.embedding_dimensions,
        llm_model=config.llm_model,
        has_api_key=bool(config.encrypted_api_key),
        connection_status=config.connection_status,
    )


@router.put("/settings/ai-provider", response_model=AIProviderConfigResponse)
async def update_ai_provider_config(
    payload: AIProviderUpdatePayload,
    session: AsyncSession = Depends(get_db),
    token=Depends(auth_middleware),
):
    org_id = token.org_id
    from services.tenant_helpers import set_tenant_context

    await set_tenant_context(session, org_id)

    if payload.provider not in ("openai", "gemini"):
        raise HTTPException(
            status_code=400, detail="Invalid provider. Must be 'openai' or 'gemini'"
        )

    if payload.api_key and len(payload.api_key) < 10:
        raise HTTPException(status_code=400, detail="API key is too short")

    config = AIProviderSettings.get_or_create(session, org_id)

    config.provider = payload.provider
    if payload.api_key:
        config.set_api_key(payload.api_key)
    config.connection_status = "untested"

    if payload.embedding_model:
        config.embedding_model = payload.embedding_model
    else:
        if payload.provider == "gemini":
            config.embedding_model = "gemini-embedding-001"
            config.embedding_dimensions = 3072
        else:
            config.embedding_model = "text-embedding-3-small"
            config.embedding_dimensions = 1536

    if payload.llm_model:
        config.llm_model = payload.llm_model
    else:
        config.llm_model = (
            "gemini-2.0-flash" if payload.provider == "gemini" else "gpt-4o-mini"
        )

    session.add(config)
    await session.commit()
    await session.refresh(config)

    return AIProviderConfigResponse(
        provider=config.provider,
        embedding_model=config.embedding_model,
        embedding_dimensions=config.embedding_dimensions,
        llm_model=config.llm_model,
        has_api_key=bool(config.encrypted_api_key),
        connection_status=config.connection_status,
    )


@router.get("/settings/ai-provider/models")
async def get_available_models(
    token=Depends(auth_middleware),
):
    return PROVIDER_MODELS


@router.post("/settings/ai-provider/test", response_model=ConnectionTestResponse)
async def test_ai_provider_connection(
    session: AsyncSession = Depends(get_db),
    token=Depends(auth_middleware),
):
    org_id = token.org_id
    from services.tenant_helpers import set_tenant_context

    await set_tenant_context(session, org_id)

    config = AIProviderSettings.get_for_org(session, org_id)
    if not config or not config.encrypted_api_key:
        return ConnectionTestResponse(success=False, message="No API key configured")

    api_key = config.get_api_key()
    if not api_key:
        return ConnectionTestResponse(
            success=False, message="Failed to decrypt API key"
        )

    try:
        if config.provider == "openai":
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=api_key)
            models = await client.models.list()
            config.connection_status = "connected"
        elif config.provider == "gemini":
            from google import genai

            _client = genai.Client(api_key=api_key)
            list(_client.models.list())
            config.connection_status = "connected"
        else:
            return ConnectionTestResponse(success=False, message="Unknown provider")

        session.add(config)
        await session.commit()
        return ConnectionTestResponse(
            success=True, message=f"Successfully connected to {config.provider}"
        )

    except Exception as e:
        config.connection_status = "disconnected"
        session.add(config)
        await session.commit()
        logger.warning(f"AI provider connection test failed: {e}")
        return ConnectionTestResponse(
            success=False, message=f"Connection failed: {str(e)[:200]}"
        )
