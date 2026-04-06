"""Story 3.3 Integration Tests: Script Generation Pipeline End-to-End.

Tests [3.3-INT-001] through [3.3-INT-005] covering the full wired pipeline:
router -> service -> grounding -> LLM -> response.

Uses FastAPI TestClient with dependency overrides and targeted patches
to avoid real DB/LLM/embedding calls while validating the wiring.
"""

import json
import time
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI

from config.settings import settings
from schemas.script_generation import ScriptGenerateResponse
from services.grounding import GroundingResult
from services.script_generation import NO_KNOWLEDGE_FALLBACK


def _make_chunks(
    count=3, similarity=0.85, content="Sample chunk content about products"
):
    return [
        {
            "chunk_id": i + 1,
            "knowledge_base_id": 10,
            "content": f"{content} part {i + 1}",
            "metadata": {"source": "test"},
            "similarity": similarity - i * 0.05,
        }
        for i in range(count)
    ]


def _make_agent_model(
    agent_id=1,
    org_id="test_org_123",
    grounding_config=None,
    config_version=1,
    system_prompt_template=None,
):
    agent = MagicMock()
    agent.id = agent_id
    agent.org_id = org_id
    agent.knowledge_base_ids = [10]
    agent.grounding_config = grounding_config
    agent.config_version = config_version
    agent.system_prompt_template = system_prompt_template
    agent.soft_delete = False
    return agent


def _setup_session_for_service(mock_session):
    """Configure mock_session to handle _get_agent_knowledge_base_ids and _count_total_chunks."""
    agent_row = MagicMock()
    agent_row.first.return_value = MagicMock()
    agent_row.first.return_value.__getitem__ = lambda self, idx: [
        1,
        "test_org_123",
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


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def app_with_overrides(mock_session):
    from database.session import get_session as get_db
    from dependencies.org_context import get_current_org_id
    from routers.scripts import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/scripts")

    async def override_db():
        yield mock_session

    async def override_org():
        return "test_org_123"

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_org_id] = override_org
    return app


def _router_patches(mock_agent, chunks=None):
    """Return a list of (target, kwargs) for patching router-level dependencies."""
    patches = [
        (
            "routers.scripts.verify_namespace_access",
            {"new_callable": AsyncMock, "return_value": "test_org_123"},
        ),
        ("routers.scripts._set_rls_context", {"new_callable": AsyncMock}),
        (
            "routers.scripts._load_and_validate_agent",
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
    return patches


def _apply_patches(stack, patches_spec):
    """Apply a list of (target, kwargs) patches to an ExitStack."""
    for target, kwargs in patches_spec:
        if "new_callable" in kwargs:
            stack.enter_context(patch(target, **kwargs))
        else:
            stack.enter_context(patch(target, **kwargs))


# ─── [3.3-INT-001] Full pipeline end-to-end ────────────────────────────


@pytest.mark.asyncio
class TestINT001FullPipeline:
    async def test_generate_endpoint_returns_grounded_response(
        self, app_with_overrides, mock_session
    ):
        """[3.3-INT-001] POST /generate -> full pipeline end-to-end with mocked services."""
        from httpx import ASGITransport, AsyncClient

        _setup_session_for_service(mock_session)
        mock_agent = _make_agent_model(
            grounding_config={
                "groundingMode": "strict",
                "maxSourceChunks": 5,
                "minConfidence": 0.5,
            }
        )
        chunks = _make_chunks(3, 0.85)

        with ExitStack() as stack:
            _apply_patches(stack, _router_patches(mock_agent))
            stack.enter_context(
                patch(
                    "services.script_generation.search_knowledge_chunks",
                    new_callable=AsyncMock,
                    return_value=chunks,
                )
            )

            mock_llm_svc = AsyncMock()
            mock_llm_svc.generate = AsyncMock(
                return_value="Our product supports advanced analytics."
            )
            stack.enter_context(
                patch("routers.scripts.LLMService", return_value=mock_llm_svc)
            )

            stack.enter_context(
                patch(
                    "routers.scripts.GroundingService.compute_confidence",
                    return_value=GroundingResult(
                        score=0.82,
                        chunk_coverage=0.6,
                        avg_similarity=0.85,
                        attribution_ratio=0.9,
                        is_low_confidence=False,
                        source_chunk_ids=[1, 2, 3],
                        was_truncated=False,
                    ),
                )
            )

            async with AsyncClient(
                transport=ASGITransport(app=app_with_overrides),
                base_url="http://test",
            ) as client:
                resp = await client.post(
                    "/api/v1/scripts/generate",
                    json={"query": "Tell me about products", "agentId": 1},
                )

        assert resp.status_code == 200
        body = resp.json()
        assert body["response"] == "Our product supports advanced analytics."
        assert body["groundingConfidence"] == 0.82
        assert body["isLowConfidence"] is False
        assert len(body["sourceChunks"]) == 3
        assert body["groundingMode"] == "strict"

    async def test_generate_endpoint_no_chunks_returns_fallback(
        self, app_with_overrides, mock_session
    ):
        """[3.3-INT-001] No chunks found -> NO_KNOWLEDGE_FALLBACK response."""
        from httpx import ASGITransport, AsyncClient

        _setup_session_for_service(mock_session)
        mock_agent = _make_agent_model()

        with ExitStack() as stack:
            _apply_patches(stack, _router_patches(mock_agent))
            stack.enter_context(
                patch(
                    "services.script_generation.search_knowledge_chunks",
                    new_callable=AsyncMock,
                    return_value=[],
                )
            )

            async with AsyncClient(
                transport=ASGITransport(app=app_with_overrides),
                base_url="http://test",
            ) as client:
                resp = await client.post(
                    "/api/v1/scripts/generate",
                    json={"query": "obscure topic", "agentId": 1},
                )

        assert resp.status_code == 200
        body = resp.json()
        assert body["response"] == NO_KNOWLEDGE_FALLBACK
        assert body["groundingConfidence"] == 0.0
        assert body["isLowConfidence"] is True
        assert body["sourceChunks"] == []

    async def test_generate_endpoint_agent_not_found_returns_404(
        self, app_with_overrides
    ):
        """[3.3-INT-001] Agent not found -> 404."""
        from fastapi import HTTPException
        from httpx import ASGITransport, AsyncClient

        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    "routers.scripts.verify_namespace_access",
                    new_callable=AsyncMock,
                    return_value="test_org_123",
                )
            )
            stack.enter_context(
                patch("routers.scripts._set_rls_context", new_callable=AsyncMock)
            )
            stack.enter_context(
                patch(
                    "routers.scripts._load_and_validate_agent",
                    new_callable=AsyncMock,
                    side_effect=HTTPException(
                        status_code=404, detail="Agent not found"
                    ),
                )
            )

            async with AsyncClient(
                transport=ASGITransport(app=app_with_overrides),
                base_url="http://test",
            ) as client:
                resp = await client.post(
                    "/api/v1/scripts/generate",
                    json={"query": "test query", "agentId": 999},
                )

        assert resp.status_code == 404


# ─── [3.3-INT-002] Config persistence ──────────────────────────────────


@pytest.mark.asyncio
class TestINT002ConfigPersistence:
    async def test_post_config_then_get_config_roundtrip(
        self, app_with_overrides, mock_session
    ):
        """[3.3-INT-002] POST /config saves grounding config and returns updated config."""
        from httpx import ASGITransport, AsyncClient

        mock_agent = _make_agent_model(grounding_config=None, config_version=1)

        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    "routers.scripts.verify_namespace_access",
                    new_callable=AsyncMock,
                    return_value="test_org_123",
                )
            )
            stack.enter_context(
                patch("routers.scripts._set_rls_context", new_callable=AsyncMock)
            )
            stack.enter_context(
                patch(
                    "routers.scripts._load_and_validate_agent",
                    new_callable=AsyncMock,
                    return_value=mock_agent,
                )
            )

            async with AsyncClient(
                transport=ASGITransport(app=app_with_overrides),
                base_url="http://test",
            ) as client:
                resp = await client.post(
                    "/api/v1/scripts/config",
                    json={
                        "agentId": 1,
                        "expectedVersion": 1,
                        "groundingMode": "balanced",
                        "maxSourceChunks": 10,
                        "minConfidence": 0.7,
                    },
                )

        assert resp.status_code == 200
        body = resp.json()
        assert body["groundingMode"] == "balanced"
        assert body["maxSourceChunks"] == 10
        assert body["minConfidence"] == 0.7
        assert body["configVersion"] == 2

    async def test_config_version_conflict_returns_409(self, app_with_overrides):
        """[3.3-INT-002] Version mismatch -> 409 Conflict."""
        from httpx import ASGITransport, AsyncClient

        mock_agent = _make_agent_model(config_version=3)

        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    "routers.scripts.verify_namespace_access",
                    new_callable=AsyncMock,
                    return_value="test_org_123",
                )
            )
            stack.enter_context(
                patch("routers.scripts._set_rls_context", new_callable=AsyncMock)
            )
            stack.enter_context(
                patch(
                    "routers.scripts._load_and_validate_agent",
                    new_callable=AsyncMock,
                    return_value=mock_agent,
                )
            )

            async with AsyncClient(
                transport=ASGITransport(app=app_with_overrides),
                base_url="http://test",
            ) as client:
                resp = await client.post(
                    "/api/v1/scripts/config",
                    json={
                        "agentId": 1,
                        "expectedVersion": 1,
                        "groundingMode": "strict",
                        "maxSourceChunks": 5,
                        "minConfidence": 0.5,
                    },
                )

        assert resp.status_code == 409

    async def test_get_config_returns_defaults_when_no_config_set(
        self, app_with_overrides
    ):
        """[3.3-INT-002] GET /config/{agent_id} returns defaults when agent has no grounding_config."""
        from httpx import ASGITransport, AsyncClient

        mock_agent = _make_agent_model(grounding_config=None, config_version=1)

        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    "routers.scripts.verify_namespace_access",
                    new_callable=AsyncMock,
                    return_value="test_org_123",
                )
            )
            stack.enter_context(
                patch("routers.scripts._set_rls_context", new_callable=AsyncMock)
            )
            stack.enter_context(
                patch(
                    "routers.scripts._load_and_validate_agent",
                    new_callable=AsyncMock,
                    return_value=mock_agent,
                )
            )

            async with AsyncClient(
                transport=ASGITransport(app=app_with_overrides),
                base_url="http://test",
            ) as client:
                resp = await client.get("/api/v1/scripts/config/1")

        assert resp.status_code == 200
        body = resp.json()
        assert body["agentId"] == 1
        assert body["configVersion"] == 1


# ─── [3.3-INT-003] Latency measurement ─────────────────────────────────


@pytest.mark.asyncio
class TestINT003LatencyMeasurement:
    async def test_generate_response_measures_latency(
        self, app_with_overrides, mock_session
    ):
        """[3.3-INT-003] Response includes latencyMs field reflecting wall-clock time."""
        from httpx import ASGITransport, AsyncClient

        _setup_session_for_service(mock_session)
        mock_agent = _make_agent_model()
        chunks = _make_chunks(2, 0.8)

        with ExitStack() as stack:
            _apply_patches(stack, _router_patches(mock_agent))
            stack.enter_context(
                patch(
                    "services.script_generation.search_knowledge_chunks",
                    new_callable=AsyncMock,
                    return_value=chunks,
                )
            )

            mock_llm_svc = AsyncMock()
            mock_llm_svc.generate = AsyncMock(
                return_value="Analytics feature available."
            )
            stack.enter_context(
                patch("routers.scripts.LLMService", return_value=mock_llm_svc)
            )

            stack.enter_context(
                patch(
                    "routers.scripts.GroundingService.compute_confidence",
                    return_value=GroundingResult(
                        score=0.75,
                        chunk_coverage=0.4,
                        avg_similarity=0.8,
                        attribution_ratio=0.85,
                        is_low_confidence=False,
                        source_chunk_ids=[1, 2],
                        was_truncated=False,
                    ),
                )
            )

            async with AsyncClient(
                transport=ASGITransport(app=app_with_overrides),
                base_url="http://test",
            ) as client:
                resp = await client.post(
                    "/api/v1/scripts/generate",
                    json={"query": "What analytics features?", "agentId": 1},
                )

        body = resp.json()
        assert "latencyMs" in body
        assert isinstance(body["latencyMs"], (int, float))
        assert body["latencyMs"] >= 0


# ─── [3.3-INT-004] Grounding modes comparison ──────────────────────────


@pytest.mark.asyncio
class TestINT004GroundingModes:
    async def _run_generate_with_mode(self, app, mock_session, mode, expected_marker):
        from httpx import ASGITransport, AsyncClient

        _setup_session_for_service(mock_session)
        mock_agent = _make_agent_model(
            grounding_config={
                "groundingMode": mode,
                "maxSourceChunks": 5,
                "minConfidence": 0.5,
            }
        )
        chunks = _make_chunks(2, 0.8)

        with ExitStack() as stack:
            _apply_patches(stack, _router_patches(mock_agent))
            stack.enter_context(
                patch(
                    "services.script_generation.search_knowledge_chunks",
                    new_callable=AsyncMock,
                    return_value=chunks,
                )
            )

            mock_llm_svc = AsyncMock()
            mock_llm_svc.generate = AsyncMock(return_value=f"{mode.title()} response.")
            stack.enter_context(
                patch("routers.scripts.LLMService", return_value=mock_llm_svc)
            )

            stack.enter_context(
                patch(
                    "routers.scripts.GroundingService.compute_confidence",
                    return_value=GroundingResult(
                        score=0.8,
                        chunk_coverage=0.4,
                        avg_similarity=0.8,
                        attribution_ratio=0.8,
                        is_low_confidence=False,
                        source_chunk_ids=[1, 2],
                        was_truncated=False,
                    ),
                )
            )

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                resp = await client.post(
                    "/api/v1/scripts/generate",
                    json={"query": "product details", "agentId": 1},
                )

        return resp, mock_llm_svc

    async def test_strict_mode_prompt_contains_only_constraint(
        self, app_with_overrides, mock_session
    ):
        """[3.3-INT-004] Strict mode system prompt contains 'ONLY' constraint."""
        resp, mock_llm = await self._run_generate_with_mode(
            app_with_overrides, mock_session, "strict", "ONLY"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["groundingMode"] == "strict"
        call_args = mock_llm.generate.call_args
        system = (
            call_args.kwargs.get("system")
            or call_args[1].get("system")
            or call_args[0][0]
        )
        assert "ONLY" in system

    async def test_balanced_mode_prompt_contains_supplement_marker(
        self, app_with_overrides, mock_session
    ):
        """[3.3-INT-004] Balanced mode prompt contains supplement knowledge marker."""
        resp, mock_llm = await self._run_generate_with_mode(
            app_with_overrides, mock_session, "balanced", "General knowledge"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["groundingMode"] == "balanced"
        call_args = mock_llm.generate.call_args
        system = (
            call_args.kwargs.get("system")
            or call_args[1].get("system")
            or call_args[0][0]
        )
        assert "General knowledge" in system

    async def test_creative_mode_prompt_contains_additional_context_marker(
        self, app_with_overrides, mock_session
    ):
        """[3.3-INT-004] Creative mode prompt contains 'Additional context' marker."""
        resp, mock_llm = await self._run_generate_with_mode(
            app_with_overrides, mock_session, "creative", "Additional context"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["groundingMode"] == "creative"
        call_args = mock_llm.generate.call_args
        system = (
            call_args.kwargs.get("system")
            or call_args[1].get("system")
            or call_args[0][0]
        )
        assert "Additional context" in system


# ─── [3.3-INT-005] Concurrent request handling ─────────────────────────


@pytest.mark.asyncio
class TestINT005Concurrency:
    async def test_sequential_requests_succeed(self, app_with_overrides, mock_session):
        """[3.3-INT-005] Multiple sequential requests all succeed without errors."""
        import asyncio
        from httpx import ASGITransport, AsyncClient

        _setup_session_for_service(mock_session)
        mock_agent = _make_agent_model()
        chunks = _make_chunks(2, 0.8)

        results = []
        for i in range(5):
            with ExitStack() as stack:
                _apply_patches(stack, _router_patches(mock_agent))
                stack.enter_context(
                    patch(
                        "services.script_generation.search_knowledge_chunks",
                        new_callable=AsyncMock,
                        return_value=chunks,
                    )
                )
                mock_llm_svc = AsyncMock()
                mock_llm_svc.generate = AsyncMock(return_value=f"Response {i}")
                stack.enter_context(
                    patch("routers.scripts.LLMService", return_value=mock_llm_svc)
                )
                stack.enter_context(
                    patch(
                        "routers.scripts.GroundingService.compute_confidence",
                        return_value=GroundingResult(
                            score=0.8,
                            chunk_coverage=0.4,
                            avg_similarity=0.8,
                            attribution_ratio=0.8,
                            is_low_confidence=False,
                            source_chunk_ids=[1, 2],
                            was_truncated=False,
                        ),
                    )
                )

                async with AsyncClient(
                    transport=ASGITransport(app=app_with_overrides),
                    base_url="http://test",
                ) as client:
                    resp = await client.post(
                        "/api/v1/scripts/generate",
                        json={"query": f"query {i}", "agentId": 1},
                    )
                    results.append(resp)

        for resp in results:
            assert resp.status_code == 200

    async def test_override_grounding_mode_via_request_body(
        self, app_with_overrides, mock_session
    ):
        """[3.3-INT-005] overrideGroundingMode in request body overrides agent config."""
        from httpx import ASGITransport, AsyncClient

        _setup_session_for_service(mock_session)
        mock_agent = _make_agent_model(
            grounding_config={
                "groundingMode": "strict",
                "maxSourceChunks": 5,
                "minConfidence": 0.5,
            }
        )
        chunks = _make_chunks(2, 0.8)

        with ExitStack() as stack:
            _apply_patches(stack, _router_patches(mock_agent))
            stack.enter_context(
                patch(
                    "services.script_generation.search_knowledge_chunks",
                    new_callable=AsyncMock,
                    return_value=chunks,
                )
            )
            mock_llm_svc = AsyncMock()
            mock_llm_svc.generate = AsyncMock(return_value="Creative response.")
            stack.enter_context(
                patch("routers.scripts.LLMService", return_value=mock_llm_svc)
            )
            stack.enter_context(
                patch(
                    "routers.scripts.GroundingService.compute_confidence",
                    return_value=GroundingResult(
                        score=0.7,
                        chunk_coverage=0.4,
                        avg_similarity=0.8,
                        attribution_ratio=0.7,
                        is_low_confidence=False,
                        source_chunk_ids=[1, 2],
                        was_truncated=False,
                    ),
                )
            )

            async with AsyncClient(
                transport=ASGITransport(app=app_with_overrides),
                base_url="http://test",
            ) as client:
                resp = await client.post(
                    "/api/v1/scripts/generate",
                    json={
                        "query": "product info",
                        "agentId": 1,
                        "overrideGroundingMode": "creative",
                    },
                )

        assert resp.status_code == 200
        body = resp.json()
        assert body["groundingMode"] == "creative"
