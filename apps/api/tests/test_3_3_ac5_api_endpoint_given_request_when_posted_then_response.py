"""Story 3.3 AC5: API Endpoint.

Tests [3.3-UNIT-022] through [3.3-UNIT-028].
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from conftest_3_3 import (
    TEST_ORG,
    create_test_app,
    make_agent_model,
    make_script_result,
)
from services.script_generation import ScriptGenerationResult


@pytest.mark.p1
class TestAC5APIEndpoint:
    def test_3_3_022_given_valid_query_when_post_generate_then_returns_response(
        self, mock_session
    ):
        """[3.3-UNIT-022] POST /api/v1/scripts/generate returns ScriptGenerateResponse."""
        app = create_test_app(mock_session)
        mock_result = make_script_result()
        with (
            patch(
                "routers.scripts.verify_namespace_access",
                new_callable=AsyncMock,
                return_value=TEST_ORG,
            ),
            patch("routers.scripts.set_rls_context", new_callable=AsyncMock),
            patch("routers.scripts.create_llm_provider"),
            patch("routers.scripts.LLMService"),
            patch("routers.scripts._get_embedding_service"),
            patch("routers.scripts.ScriptGenerationService") as mock_svc_cls,
        ):
            mock_svc = AsyncMock()
            mock_svc.generate_response = AsyncMock(return_value=mock_result)
            mock_svc_cls.return_value = mock_svc

            with TestClient(app) as client:
                resp = client.post(
                    "/api/v1/scripts/generate", json={"query": "test query"}
                )
                assert resp.status_code == 200
                data = resp.json()
                assert "response" in data
                assert data["groundingConfidence"] == 0.8

    def test_3_3_024_given_empty_query_when_post_generate_then_422(self, mock_session):
        """[3.3-UNIT-024] Empty query returns 422 validation error."""
        app = create_test_app(mock_session)
        with TestClient(app) as client:
            resp = client.post("/api/v1/scripts/generate", json={"query": ""})
            assert resp.status_code == 422

    def test_3_3_025_given_agent_id_when_post_generate_then_uses_agent_config(
        self, mock_session
    ):
        """[3.3-UNIT-025] agentId triggers agent config lookup."""
        app = create_test_app(mock_session)
        agent_model = make_agent_model(
            1,
            TEST_ORG,
            grounding_config={
                "groundingMode": "balanced",
                "maxSourceChunks": 3,
                "minConfidence": 0.6,
            },
        )
        mock_result = make_script_result(
            grounding_confidence=0.7,
            grounding_mode="balanced",
            latency_ms=50.0,
        )
        with (
            patch(
                "routers.scripts.verify_namespace_access",
                new_callable=AsyncMock,
                return_value=TEST_ORG,
            ),
            patch("routers.scripts.set_rls_context", new_callable=AsyncMock),
            patch(
                "routers.scripts.load_agent_for_context",
                new_callable=AsyncMock,
                return_value=agent_model,
            ),
            patch("routers.scripts.create_llm_provider"),
            patch("routers.scripts.LLMService"),
            patch("routers.scripts._get_embedding_service"),
            patch("routers.scripts.ScriptGenerationService") as mock_svc_cls,
        ):
            mock_svc = AsyncMock()
            mock_svc.generate_response = AsyncMock(return_value=mock_result)
            mock_svc_cls.return_value = mock_svc

            with TestClient(app) as client:
                resp = client.post(
                    "/api/v1/scripts/generate", json={"query": "test", "agentId": 1}
                )
                assert resp.status_code == 200
                call_kwargs = mock_svc.generate_response.call_args.kwargs
                assert call_kwargs.get("grounding_mode") == "balanced"

    def test_3_3_026_given_override_params_when_post_generate_then_overrides_applied(
        self, mock_session
    ):
        """[3.3-UNIT-026] Override params take precedence."""
        app = create_test_app(mock_session)
        mock_result = make_script_result(
            grounding_confidence=0.7,
            grounding_mode="creative",
            latency_ms=50.0,
        )
        with (
            patch(
                "routers.scripts.verify_namespace_access",
                new_callable=AsyncMock,
                return_value=TEST_ORG,
            ),
            patch("routers.scripts.set_rls_context", new_callable=AsyncMock),
            patch("routers.scripts.create_llm_provider"),
            patch("routers.scripts.LLMService"),
            patch("routers.scripts._get_embedding_service"),
            patch("routers.scripts.ScriptGenerationService") as mock_svc_cls,
        ):
            mock_svc = AsyncMock()
            mock_svc.generate_response = AsyncMock(return_value=mock_result)
            mock_svc_cls.return_value = mock_svc

            with TestClient(app) as client:
                resp = client.post(
                    "/api/v1/scripts/generate",
                    json={
                        "query": "test",
                        "overrideGroundingMode": "creative",
                        "overrideMaxChunks": 3,
                    },
                )
                assert resp.status_code == 200
                call_kwargs = mock_svc.generate_response.call_args.kwargs
                assert call_kwargs.get("grounding_mode") == "creative"
                assert call_kwargs.get("max_source_chunks") == 3

    def test_3_3_027_given_nonexistent_agent_when_post_generate_then_404(
        self, mock_session
    ):
        """[3.3-UNIT-027] Non-existent agentId returns 404."""
        app = create_test_app(mock_session)
        with (
            patch(
                "routers.scripts.verify_namespace_access",
                new_callable=AsyncMock,
                return_value=TEST_ORG,
            ),
            patch("routers.scripts.set_rls_context", new_callable=AsyncMock),
            patch(
                "routers.scripts.load_agent_for_context",
                new_callable=AsyncMock,
                side_effect=__import__("fastapi").HTTPException(
                    status_code=404, detail="Agent not found"
                ),
            ),
        ):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post(
                    "/api/v1/scripts/generate", json={"query": "test", "agentId": 9999}
                )
                assert resp.status_code == 404

    def test_3_3_028_given_cross_org_agent_when_post_generate_then_403(
        self, mock_session
    ):
        """[3.3-UNIT-028] Cross-org agentId returns 403."""
        app = create_test_app(mock_session)
        with (
            patch(
                "routers.scripts.verify_namespace_access",
                new_callable=AsyncMock,
                return_value=TEST_ORG,
            ),
            patch("routers.scripts.set_rls_context", new_callable=AsyncMock),
            patch(
                "routers.scripts.load_agent_for_context",
                new_callable=AsyncMock,
                side_effect=__import__("fastapi").HTTPException(
                    status_code=403, detail="Agent belongs to different organization"
                ),
            ),
        ):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post(
                    "/api/v1/scripts/generate", json={"query": "test", "agentId": 1}
                )
                assert resp.status_code == 403
