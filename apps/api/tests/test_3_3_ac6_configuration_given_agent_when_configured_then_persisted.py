"""Story 3.3 AC6: Configuration.

Tests [3.3-UNIT-029] through [3.3-UNIT-037].
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from conftest_3_3 import TEST_ORG, create_test_app, make_agent_model
from config.settings import settings


@pytest.mark.p3
class TestAC6Configuration:
    def test_3_3_029_given_valid_config_when_post_config_then_persisted(
        self, mock_session
    ):
        """[3.3-UNIT-029] Config persisted to agent record."""
        app = create_test_app(mock_session)
        agent = make_agent_model(1, TEST_ORG, config_version=1)
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
                return_value=agent,
            ),
        ):
            with TestClient(app) as client:
                resp = client.post(
                    "/api/v1/scripts/config",
                    json={
                        "agentId": 1,
                        "expectedVersion": 1,
                        "groundingMode": "strict",
                        "maxSourceChunks": 5,
                        "minConfidence": 0.6,
                    },
                )
                assert resp.status_code == 200
                assert agent.grounding_config is not None
                assert agent.config_version == 2

    def test_3_3_030_given_invalid_mode_when_post_config_then_422(self, mock_session):
        """[3.3-UNIT-030] Invalid grounding_mode returns 422."""
        app = create_test_app(mock_session)
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/scripts/config",
                json={
                    "agentId": 1,
                    "expectedVersion": 1,
                    "groundingMode": "invalid_mode",
                    "maxSourceChunks": 5,
                    "minConfidence": 0.5,
                },
            )
            assert resp.status_code == 422

    def test_3_3_031_given_invalid_confidence_when_post_config_then_422(
        self, mock_session
    ):
        """[3.3-UNIT-031] min_confidence > 1.0 returns 422."""
        app = create_test_app(mock_session)
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/scripts/config",
                json={
                    "agentId": 1,
                    "expectedVersion": 1,
                    "groundingMode": "strict",
                    "maxSourceChunks": 5,
                    "minConfidence": 1.5,
                },
            )
            assert resp.status_code == 422

    def test_3_3_032_given_get_config_when_called_then_returns_current(
        self, mock_session
    ):
        """[3.3-UNIT-032] GET config returns current config."""
        app = create_test_app(mock_session)
        agent = make_agent_model(
            1,
            TEST_ORG,
            grounding_config={
                "groundingMode": "balanced",
                "maxSourceChunks": 3,
                "minConfidence": 0.6,
            },
            config_version=2,
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
                return_value=agent,
            ),
        ):
            with TestClient(app) as client:
                resp = client.get("/api/v1/scripts/config/1")
                assert resp.status_code == 200
                data = resp.json()
                assert data["groundingMode"] == "balanced"
                assert data["configVersion"] == 2

    def test_3_3_033_given_unconfigured_agent_when_get_config_then_returns_defaults(
        self, mock_session
    ):
        """[3.3-UNIT-033] Unconfigured agent returns defaults from settings."""
        app = create_test_app(mock_session)
        agent = make_agent_model(1, TEST_ORG, grounding_config=None, config_version=1)
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
                return_value=agent,
            ),
        ):
            with TestClient(app) as client:
                resp = client.get("/api/v1/scripts/config/1")
                assert resp.status_code == 200
                data = resp.json()
                assert data["groundingMode"] == settings.GROUNDING_DEFAULT_MODE
                assert data["maxSourceChunks"] == settings.GROUNDING_MAX_SOURCE_CHUNKS

    def test_3_3_034_given_stale_version_when_post_config_then_409(self, mock_session):
        """[3.3-UNIT-034] Stale version returns 409 Conflict."""
        app = create_test_app(mock_session)
        agent = make_agent_model(1, TEST_ORG, config_version=3)
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
                return_value=agent,
            ),
        ):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post(
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

    def test_3_3_035_given_correct_version_when_post_config_then_version_incremented(
        self, mock_session
    ):
        """[3.3-UNIT-035] Correct version → config_version incremented."""
        app = create_test_app(mock_session)
        agent = make_agent_model(1, TEST_ORG, config_version=1)
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
                return_value=agent,
            ),
        ):
            with TestClient(app) as client:
                resp = client.post(
                    "/api/v1/scripts/config",
                    json={
                        "agentId": 1,
                        "expectedVersion": 1,
                        "groundingMode": "strict",
                        "maxSourceChunks": 5,
                        "minConfidence": 0.5,
                    },
                )
                assert resp.status_code == 200
                assert agent.config_version == 2

    def test_3_3_036_given_nonexistent_agent_when_post_config_then_404(
        self, mock_session
    ):
        """[3.3-UNIT-036] Non-existent agent returns 404."""
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
                    "/api/v1/scripts/config",
                    json={
                        "agentId": 9999,
                        "expectedVersion": 1,
                        "groundingMode": "strict",
                        "maxSourceChunks": 5,
                        "minConfidence": 0.5,
                    },
                )
                assert resp.status_code == 404

    def test_3_3_037_given_cross_org_agent_when_post_config_then_403(
        self, mock_session
    ):
        """[3.3-UNIT-037] Cross-org agent returns 403."""
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
                    "/api/v1/scripts/config",
                    json={
                        "agentId": 1,
                        "expectedVersion": 1,
                        "groundingMode": "strict",
                        "maxSourceChunks": 5,
                        "minConfidence": 0.5,
                    },
                )
                assert resp.status_code == 403
