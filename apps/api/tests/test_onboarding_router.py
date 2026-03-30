"""
Story 1-6: 10-Minute Launch Onboarding Wizard
Integration Tests for Onboarding Router Endpoints

Test ID Format: [1.6-INT-XXX]
Priority: P0 (Critical) | P1 (High) | P2 (Medium)

Covers:
- POST /onboarding/complete (happy path, idempotency, auth, creation error)
- GET /onboarding/status (completed, not completed, auth)
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from routers.onboarding import router
from routers import onboarding as onboarding_mod
from database.session import get_session
from schemas.onboarding import OnboardingPayload


MOCK_ORG_ID = "org_test_onboarding_123"


def _mock_session():
    return AsyncMock()


@pytest.fixture
def app():
    application = FastAPI()
    application.include_router(router)
    application.dependency_overrides[get_session] = _mock_session

    @application.middleware("http")
    async def mock_auth(request, call_next):
        request.state.org_id = MOCK_ORG_ID
        request.state.user_id = "user_test_onboarding_456"
        response = await call_next(request)
        return response

    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def no_org_app():
    application = FastAPI()
    application.include_router(router)
    application.dependency_overrides[get_session] = _mock_session

    @application.middleware("http")
    async def mock_no_org_auth(request, call_next):
        request.state.org_id = None
        request.state.user_id = None
        response = await call_next(request)
        return response

    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def no_org_client(no_org_app):
    return TestClient(no_org_app, raise_server_exceptions=False)


def _make_agent_record(agent_id=1, onboarding_complete=True):
    from models.agent import Agent

    agent = Agent.model_validate(
        {
            "name": "My First Agent",
            "voiceId": "avery",
            "businessGoal": "Lead generation",
            "safetyLevel": "strict",
            "integrationType": "gohighlevel",
            "onboardingComplete": onboarding_complete,
        }
    )
    agent.id = agent_id
    agent.org_id = MOCK_ORG_ID
    return agent


def _make_script_record(script_id=1, agent_id=1):
    from models.script import Script

    script = Script.model_validate(
        {
            "agentId": agent_id,
            "name": "Initial Script",
            "content": "",
            "version": 1,
            "scriptContext": "We sell premium widgets to small businesses across the nation",
        }
    )
    script.id = script_id
    script.org_id = MOCK_ORG_ID
    return script


VALID_PAYLOAD = {
    "businessGoal": "Lead generation",
    "scriptContext": "We sell premium widgets to small businesses across the nation",
    "voiceId": "avery",
    "integrationType": "gohighlevel",
    "safetyLevel": "strict",
}


class TestCompleteOnboarding:
    """[1.6-INT-001..005] POST /onboarding/complete integration tests"""

    def test_1_6_int_001_complete_onboarding_happy_path(self, client):
        # Given: Organization with no existing agents
        # When: POST /onboarding/complete with valid payload
        agent = _make_agent_record()
        script = _make_script_record()

        mock_agent_svc = MagicMock()
        mock_agent_svc.list_all = AsyncMock(return_value=[])
        mock_agent_svc.create = AsyncMock(return_value=agent)
        mock_script_svc = MagicMock()
        mock_script_svc.create = AsyncMock(return_value=script)

        with (
            patch.object(onboarding_mod, "_agent_service", mock_agent_svc),
            patch.object(onboarding_mod, "_script_service", mock_script_svc),
        ):
            response = client.post("/onboarding/complete", json=VALID_PAYLOAD)

        # Then: Returns 201 with agent and script
        assert response.status_code == 201
        data = response.json()
        assert "agent" in data
        assert "script" in data
        assert data["agent"]["name"] == "My First Agent"
        assert data["script"]["name"] == "Initial Script"

    def test_1_6_int_002_idempotency_guard(self, client):
        # Given: Organization already has a completed agent
        # When: POST /onboarding/complete again
        existing_agent = _make_agent_record(onboarding_complete=True)

        mock_agent_svc = MagicMock()
        mock_agent_svc.list_all = AsyncMock(return_value=[existing_agent])

        with patch.object(onboarding_mod, "_agent_service", mock_agent_svc):
            response = client.post("/onboarding/complete", json=VALID_PAYLOAD)

        # Then: Returns 400 with ONBOARDING_ALREADY_COMPLETE
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["code"] == "ONBOARDING_ALREADY_COMPLETE"

    def test_1_6_int_003_missing_org_context(self, no_org_client):
        # Given: Request without org_id in state
        # When: POST /onboarding/complete
        response = no_org_client.post("/onboarding/complete", json=VALID_PAYLOAD)

        # Then: Returns 403 with AUTH_FORBIDDEN
        assert response.status_code == 403
        data = response.json()
        assert data["detail"]["code"] == "AUTH_FORBIDDEN"

    def test_1_6_int_004_creation_failure(self, client):
        # Given: Agent creation raises an unexpected exception
        # When: POST /onboarding/complete
        mock_agent_svc = MagicMock()
        mock_agent_svc.list_all = AsyncMock(return_value=[])
        mock_agent_svc.create = AsyncMock(side_effect=Exception("DB connection lost"))

        with patch.object(onboarding_mod, "_agent_service", mock_agent_svc):
            response = client.post("/onboarding/complete", json=VALID_PAYLOAD)

        # Then: Returns 500 with ONBOARDING_CREATE_ERROR
        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["code"] == "ONBOARDING_CREATE_ERROR"

    def test_1_6_int_005_invalid_payload_rejected(self, client):
        # Given: Payload with invalid safety_level
        # When: POST /onboarding/complete
        invalid_payload = {
            **VALID_PAYLOAD,
            "safetyLevel": "invalid_level",
        }

        response = client.post("/onboarding/complete", json=invalid_payload)

        # Then: Returns 422 validation error
        assert response.status_code == 422


class TestGetOnboardingStatus:
    """[1.6-INT-006..009] GET /onboarding/status integration tests"""

    def test_1_6_int_006_status_completed(self, client):
        # Given: A session mock that returns a completed agent row
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.first.return_value = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        app_with_session = FastAPI()
        app_with_session.include_router(router)
        app_with_session.dependency_overrides[get_session] = lambda: mock_session

        @app_with_session.middleware("http")
        async def mock_auth(request, call_next):
            request.state.org_id = MOCK_ORG_ID
            request.state.user_id = "user_test_456"
            response = await call_next(request)
            return response

        test_client = TestClient(app_with_session, raise_server_exceptions=False)

        # When: GET /onboarding/status
        response = test_client.get("/onboarding/status")

        # Then: Returns {completed: true}
        assert response.status_code == 200
        assert response.json() == {"completed": True}

    def test_1_6_int_007_status_not_completed(self, client):
        # Given: A session mock that returns no rows
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.first.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        app_with_session = FastAPI()
        app_with_session.include_router(router)
        app_with_session.dependency_overrides[get_session] = lambda: mock_session

        @app_with_session.middleware("http")
        async def mock_auth(request, call_next):
            request.state.org_id = MOCK_ORG_ID
            request.state.user_id = "user_test_456"
            response = await call_next(request)
            return response

        test_client = TestClient(app_with_session, raise_server_exceptions=False)

        # When: GET /onboarding/status
        response = test_client.get("/onboarding/status")

        # Then: Returns {completed: false}
        assert response.status_code == 200
        assert response.json() == {"completed": False}

    def test_1_6_int_008_status_missing_org_context(self, no_org_client):
        # Given: Request without org_id in state
        # When: GET /onboarding/status
        response = no_org_client.get("/onboarding/status")

        # Then: Returns 403 with AUTH_FORBIDDEN
        assert response.status_code == 403
        data = response.json()
        assert data["detail"]["code"] == "AUTH_FORBIDDEN"

    def test_1_6_int_009_status_skips_soft_deleted_agents(self):
        # Given: The raw SQL query filters by soft_delete = false
        # This validates the SQL query text directly
        from pathlib import Path

        source = Path(onboarding_mod.__file__).read_text()
        assert "soft_delete = false" in source
        assert "onboarding_complete = true" in source
