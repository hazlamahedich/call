"""Shared fixtures for Story 3.3 Script Generation tests.

Provides reusable test factories, fixtures for mock services, and FastAPI app setup.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from config.settings import settings
from services.llm.service import LLMService


from services.grounding import GroundingService, GroundingResult
from services.script_generation import (
    NO_KNOWLEDGE_FALLBACK,
    ScriptGenerationResult,
    ScriptGenerationService,
)
from schemas.script_generation import (
    ScriptGenerateRequest,
    ScriptGenerateResponse,
    SourceChunkInfo,
)


TEST_ORG = "test_org_123"


def make_chunks(
    count=3,
    similarity=0.85,
    content="Sample chunk content about products",
    kb_id=10,
):
    return [
        {
            "chunk_id": i + 1,
            "knowledge_base_id": kb_id,
            "content": f"{content} part {i + 1}",
            "metadata": {"source": "test"},
            "similarity": similarity - i * 0.05,
        }
        for i in range(count)
    ]


def make_agent_model(
    agent_id=1,
    org_id=TEST_ORG,
    kb_ids=None,
    grounding_config=None,
    config_version=1,
    system_prompt_template=None,
):
    agent = MagicMock()
    agent.id = agent_id
    agent.org_id = org_id
    agent.knowledge_base_ids = kb_ids or [10]
    agent.grounding_config = grounding_config
    agent.config_version = config_version
    agent.system_prompt_template = system_prompt_template
    agent.soft_delete = False
    return agent


def make_agent_row(
    agent_id=1,
    org_id="test_org",
    kb_ids=None,
    grounding_config=None,
    config_version=1,
    system_prompt_template=None,
):
    row = MagicMock()
    row.__getitem__ = lambda self, idx: [agent_id, org_id, kb_ids or [10]][idx]
    row.first.return_value = row
    row.scalar_one_or_none.return_value = make_agent_model(
        agent_id,
        org_id,
        kb_ids,
        grounding_config,
        config_version,
        system_prompt_template,
    )
    return row


def make_script_result(**overrides):
    defaults = {
        "response": "Test response",
        "grounding_confidence": 0.8,
        "is_low_confidence": False,
        "source_chunks": [{"chunk_id": 1, "knowledge_base_id": 10, "similarity": 0.85}],
        "model": "gpt-4o-mini",
        "latency_ms": 100.0,
        "grounding_mode": "strict",
        "was_truncated": False,
        "cached": False,
    }
    defaults.update(overrides)
    return ScriptGenerationResult(**defaults)


@pytest_asyncio.fixture
async def mock_llm():
    svc = AsyncMock(spec=LLMService)
    svc.generate = AsyncMock(
        return_value="Based on our knowledge base, the product supports advanced analytics."
    )
    return svc


@pytest_asyncio.fixture
async def mock_embedding():
    svc = AsyncMock()
    svc.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
    return svc


@pytest_asyncio.fixture
async def mock_session():
    session = AsyncMock()
    count_result = MagicMock()
    count_result.scalar_one.return_value = 10
    session.execute = AsyncMock(return_value=count_result)
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session


@pytest_asyncio.fixture
async def mock_redis():
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.setex = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.scan_iter = AsyncMock(return_value=[])
    return redis


@pytest_asyncio.fixture
async def service(mock_llm, mock_embedding, mock_session, mock_redis):
    return ScriptGenerationService(
        llm_service=mock_llm,
        embedding_service=mock_embedding,
        session=mock_session,
        redis_client=mock_redis,
    )


def create_test_app(mock_session_fixture):
    from database.session import get_session as get_db
    from dependencies.org_context import get_current_org_id
    from routers.scripts import router

    app = __import__("fastapi").FastAPI()
    app.include_router(router, prefix="/api/v1/scripts")

    async def override_db():
        yield mock_session_fixture

    async def override_org():
        return TEST_ORG

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_org_id] = override_org
    return app


def setup_session_for_service(mock_session):
    agent_row = MagicMock()
    agent_row.first.return_value = MagicMock()
    agent_row.first.return_value.__getitem__ = lambda self, idx: [
        1,
        TEST_ORG,
        [10],
    ][idx]

    count_row = MagicMock()
    count_row.scalar_one.return_value = 100

    async def _execute_side_effect(query, params=None):
        query_text = str(query)
        if "knowledge_base_ids" in query_text or "FROM agents" in query_text:
            return agent_row
        return count_row

    mock_session.execute = AsyncMock(side_effect=_execute_side_effect)
    return mock_session


def router_patches(mock_agent):
    return [
        (
            "routers.scripts.verify_namespace_access",
            {"new_callable": AsyncMock, "return_value": TEST_ORG},
        ),
        ("routers.scripts.set_rls_context", {"new_callable": AsyncMock}),
        (
            "routers.scripts.load_agent_for_context",
            {"new_callable": AsyncMock, "return_value": mock_agent},
        ),
        ("routers.scripts.create_llm_provider", {"return_value": MagicMock()}),
        (
            "routers.scripts._get_embedding_service",
            {
                "return_value": MagicMock(
                    generate_embedding=AsyncMock(return_value=[0.1] * 1536)
                )
            },
        ),
    ]


def apply_patches(stack, patches_spec):
    from unittest.mock import patch

    for target, kwargs in patches_spec:
        stack.enter_context(patch(target, **kwargs))
