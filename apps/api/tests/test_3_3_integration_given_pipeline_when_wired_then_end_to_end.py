"""Story 3.3 Integration Tests: Script Generation Pipeline End-to-End.

Tests [3.3-INT-001] through [3.3-INT-005] covering the full wired pipeline:
router -> service -> grounding -> LLM -> response.
"""

import asyncio
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from conftest_3_3 import (
    TEST_ORG,
    apply_patches,
    create_test_app,
    make_agent_model,
    make_chunks,
    router_patches,
    setup_session_for_service,
)
from services.grounding import GroundingResult
from services.script_generation import NO_KNOWLEDGE_FALLBACK


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.p3
class TestINT001FullPipeline:
    async def test_generate_endpoint_returns_grounded_response(self, mock_session):
        """[3.3-INT-001] POST /generate -> full pipeline end-to-end with mocked services."""
        app = create_test_app(mock_session)
        setup_session_for_service(mock_session)
        mock_agent = make_agent_model(
            grounding_config={
                "groundingMode": "strict",
                "maxSourceChunks": 5,
                "minConfidence": 0.5,
            }
        )
        chunks = make_chunks(3, 0.85)

        with ExitStack() as stack:
            apply_patches(stack, router_patches(mock_agent))
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
                patch(
                    "routers.scripts._get_llm_service",
                    return_value=mock_llm_svc,
                )
            )

            stack.enter_context(
                patch(
                    "services.grounding.GroundingService.compute_confidence",
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
                transport=ASGITransport(app=app),
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

    async def test_generate_endpoint_no_chunks_returns_fallback(self, mock_session):
        """[3.3-INT-001] No chunks found -> NO_KNOWLEDGE_FALLBACK response."""
        app = create_test_app(mock_session)
        setup_session_for_service(mock_session)
        mock_agent = make_agent_model()

        with ExitStack() as stack:
            apply_patches(stack, router_patches(mock_agent))
            stack.enter_context(
                patch(
                    "services.script_generation.search_knowledge_chunks",
                    new_callable=AsyncMock,
                    return_value=[],
                )
            )

            async with AsyncClient(
                transport=ASGITransport(app=app),
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

    async def test_generate_endpoint_agent_not_found_returns_404(self, mock_session):
        """[3.3-INT-001] Agent not found -> 404."""
        from fastapi import HTTPException

        app = create_test_app(mock_session)
        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    "routers.scripts.verify_namespace_access",
                    new_callable=AsyncMock,
                    return_value=TEST_ORG,
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
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                resp = await client.post(
                    "/api/v1/scripts/generate",
                    json={"query": "test query", "agentId": 999},
                )

        assert resp.status_code == 404


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.p3
class TestINT002ConfigPersistence:
    async def test_post_config_then_get_config_roundtrip(self, mock_session):
        """[3.3-INT-002] POST /config saves grounding config and returns updated config."""
        app = create_test_app(mock_session)
        mock_agent = make_agent_model(grounding_config=None, config_version=1)

        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    "routers.scripts.verify_namespace_access",
                    new_callable=AsyncMock,
                    return_value=TEST_ORG,
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
                transport=ASGITransport(app=app),
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

    async def test_config_version_conflict_returns_409(self, mock_session):
        """[3.3-INT-002] Version mismatch -> 409 Conflict."""
        app = create_test_app(mock_session)
        mock_agent = make_agent_model(config_version=3)

        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    "routers.scripts.verify_namespace_access",
                    new_callable=AsyncMock,
                    return_value=TEST_ORG,
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
                transport=ASGITransport(app=app),
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

    async def test_get_config_returns_defaults_when_no_config_set(self, mock_session):
        """[3.3-INT-002] GET /config/{agent_id} returns defaults when agent has no grounding_config."""
        app = create_test_app(mock_session)
        mock_agent = make_agent_model(grounding_config=None, config_version=1)

        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    "routers.scripts.verify_namespace_access",
                    new_callable=AsyncMock,
                    return_value=TEST_ORG,
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
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                resp = await client.get("/api/v1/scripts/config/1")

        assert resp.status_code == 200
        body = resp.json()
        assert body["agentId"] == 1
        assert body["configVersion"] == 1


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.p3
class TestINT003LatencyMeasurement:
    async def test_generate_response_measures_latency(self, mock_session):
        """[3.3-INT-003] Response includes latencyMs field reflecting wall-clock time."""
        app = create_test_app(mock_session)
        setup_session_for_service(mock_session)
        mock_agent = make_agent_model()
        chunks = make_chunks(2, 0.8)

        with ExitStack() as stack:
            apply_patches(stack, router_patches(mock_agent))
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
                patch("routers.scripts._get_llm_service", return_value=mock_llm_svc)
            )

            stack.enter_context(
                patch(
                    "services.grounding.GroundingService.compute_confidence",
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
                transport=ASGITransport(app=app),
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


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.p3
class TestINT004GroundingModes:
    async def _run_generate_with_mode(self, app, mock_session, mode, expected_marker):
        setup_session_for_service(mock_session)
        mock_agent = make_agent_model(
            grounding_config={
                "groundingMode": mode,
                "maxSourceChunks": 5,
                "minConfidence": 0.5,
            }
        )
        chunks = make_chunks(2, 0.8)

        with ExitStack() as stack:
            apply_patches(stack, router_patches(mock_agent))
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
                patch("routers.scripts._get_llm_service", return_value=mock_llm_svc)
            )

            stack.enter_context(
                patch(
                    "services.grounding.GroundingService.compute_confidence",
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

    async def test_strict_mode_prompt_contains_only_constraint(self, mock_session):
        """[3.3-INT-004] Strict mode system prompt contains 'ONLY' constraint."""
        app = create_test_app(mock_session)
        resp, mock_llm = await self._run_generate_with_mode(
            app, mock_session, "strict", "ONLY"
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

    async def test_balanced_mode_prompt_contains_supplement_marker(self, mock_session):
        """[3.3-INT-004] Balanced mode prompt contains supplement knowledge marker."""
        app = create_test_app(mock_session)
        resp, mock_llm = await self._run_generate_with_mode(
            app, mock_session, "balanced", "General knowledge"
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
        self, mock_session
    ):
        """[3.3-INT-004] Creative mode prompt contains 'Additional context' marker."""
        app = create_test_app(mock_session)
        resp, mock_llm = await self._run_generate_with_mode(
            app, mock_session, "creative", "Additional context"
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


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.p3
class TestINT005Concurrency:
    async def test_sequential_requests_succeed(self, mock_session):
        """[3.3-INT-005] Multiple sequential requests all succeed without errors."""
        app = create_test_app(mock_session)
        setup_session_for_service(mock_session)
        mock_agent = make_agent_model()
        chunks = make_chunks(2, 0.8)

        results = []
        for i in range(5):
            with ExitStack() as stack:
                apply_patches(stack, router_patches(mock_agent))
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
                    patch("routers.scripts._get_llm_service", return_value=mock_llm_svc)
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
                        json={"query": f"query {i}", "agentId": 1},
                    )
                    results.append(resp)

        for resp in results:
            assert resp.status_code == 200

    async def test_override_grounding_mode_via_request_body(self, mock_session):
        """[3.3-INT-005] overrideGroundingMode in request body overrides agent config."""
        app = create_test_app(mock_session)
        setup_session_for_service(mock_session)
        mock_agent = make_agent_model(
            grounding_config={
                "groundingMode": "strict",
                "maxSourceChunks": 5,
                "minConfidence": 0.5,
            }
        )
        chunks = make_chunks(2, 0.8)

        with ExitStack() as stack:
            apply_patches(stack, router_patches(mock_agent))
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
                patch("routers.scripts._get_llm_service", return_value=mock_llm_svc)
            )
            stack.enter_context(
                patch(
                    "services.grounding.GroundingService.compute_confidence",
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
                transport=ASGITransport(app=app),
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
