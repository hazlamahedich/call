"""
Story 1.7: Resource Guardrails - Usage Monitoring & Hard Caps
Integration Tests for Usage Router Endpoints

Test ID Format: [1.7-INT-XXX]
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers.usage import router
from routers import usage as usage_mod
from database.session import get_session


MOCK_ORG_ID = "org_test_usage_123"


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
        request.state.user_id = "user_test_usage_456"
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


VALID_RECORD_PAYLOAD = {
    "resourceType": "call",
    "resourceId": "call_001",
    "action": "call_initiated",
}


class TestGetUsageSummary:
    """[1.7-INT-001..003] GET /usage/summary integration tests"""

    def test_1_7_int_001_summary_happy_path(self, client):
        mock_summary = {
            "used": 500,
            "cap": 1000,
            "percentage": 50.0,
            "plan": "free",
            "threshold": "ok",
        }

        with patch.object(
            usage_mod,
            "get_usage_summary",
            new_callable=AsyncMock,
            return_value=mock_summary,
        ):
            response = client.get("/usage/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["used"] == 500
        assert data["cap"] == 1000
        assert data["percentage"] == 50.0
        assert data["threshold"] == "ok"

    def test_1_7_int_002_summary_missing_org(self, no_org_client):
        response = no_org_client.get("/usage/summary")
        assert response.status_code == 403
        data = response.json()
        assert data["detail"]["code"] == "AUTH_FORBIDDEN"

    def test_1_7_int_003_summary_service_error(self, client):
        with patch.object(
            usage_mod,
            "get_usage_summary",
            new_callable=AsyncMock,
            side_effect=Exception("DB error"),
        ):
            response = client.get("/usage/summary")

        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["code"] == "USAGE_INTERNAL_ERROR"


class TestPostUsageRecord:
    """[1.7-INT-004..008] POST /usage/record integration tests"""

    def test_1_7_int_004_record_happy_path(self, client):
        from models.usage_log import UsageLog

        mock_log = UsageLog.model_validate(
            {
                "resourceType": "call",
                "resourceId": "call_001",
                "action": "call_initiated",
            }
        )
        mock_log.id = 1
        mock_log.org_id = MOCK_ORG_ID

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        with (
            patch(
                "middleware.usage_guard.check_usage_cap",
                new_callable=AsyncMock,
                return_value="ok",
            ),
            patch(
                "middleware.usage_guard.set_tenant_context",
                new_callable=AsyncMock,
            ),
            patch.object(
                usage_mod, "record_usage", new_callable=AsyncMock, return_value=mock_log
            ),
        ):
            response = client.post("/usage/record", json=VALID_RECORD_PAYLOAD)

        assert response.status_code == 201
        data = response.json()
        assert "usageLog" in data

    def test_1_7_int_005_record_missing_org(self, no_org_client):
        response = no_org_client.post("/usage/record", json=VALID_RECORD_PAYLOAD)
        assert response.status_code == 403

    def test_1_7_int_006_record_invalid_resource_type(self, client):
        invalid_payload = {
            **VALID_RECORD_PAYLOAD,
            "resourceType": "invalid",
        }
        response = client.post("/usage/record", json=invalid_payload)
        assert response.status_code == 422

    def test_1_7_int_007_record_invalid_action(self, client):
        invalid_payload = {
            **VALID_RECORD_PAYLOAD,
            "action": "invalid_action",
        }
        response = client.post("/usage/record", json=invalid_payload)
        assert response.status_code == 422

    def test_1_7_int_008_record_with_metadata(self, client):
        from models.usage_log import UsageLog

        mock_log = UsageLog.model_validate(
            {
                "resourceType": "call",
                "resourceId": "call_002",
                "action": "call_completed",
                "metadataJson": '{"duration": 120}',
            }
        )
        mock_log.id = 2
        mock_log.org_id = MOCK_ORG_ID

        payload = {
            **VALID_RECORD_PAYLOAD,
            "action": "call_completed",
            "metadata": '{"duration": 120}',
        }

        with (
            patch(
                "middleware.usage_guard.check_usage_cap",
                new_callable=AsyncMock,
                return_value="ok",
            ),
            patch(
                "middleware.usage_guard.set_tenant_context",
                new_callable=AsyncMock,
            ),
            patch.object(
                usage_mod, "record_usage", new_callable=AsyncMock, return_value=mock_log
            ),
        ):
            response = client.post("/usage/record", json=payload)

        assert response.status_code == 201

    def test_1_7_int_012_record_blocked_when_cap_exceeded(self, client):
        with (
            patch(
                "middleware.usage_guard.check_usage_cap",
                new_callable=AsyncMock,
                return_value="exceeded",
            ),
            patch(
                "middleware.usage_guard.set_tenant_context",
                new_callable=AsyncMock,
            ),
        ):
            response = client.post("/usage/record", json=VALID_RECORD_PAYLOAD)

        assert response.status_code == 403
        data = response.json()
        assert data["detail"]["code"] == "USAGE_LIMIT_EXCEEDED"


class TestGetUsageCheck:
    """[1.7-INT-009..011] GET /usage/check integration tests"""

    def test_1_7_int_009_check_happy_path(self, client):
        with (
            patch.object(
                usage_mod, "get_org_plan", new_callable=AsyncMock, return_value="free"
            ),
            patch.object(
                usage_mod, "check_usage_cap", new_callable=AsyncMock, return_value="ok"
            ),
            patch.object(
                usage_mod, "get_monthly_usage", new_callable=AsyncMock, return_value=500
            ),
            patch.object(
                usage_mod, "get_monthly_cap", new_callable=AsyncMock, return_value=1000
            ),
        ):
            response = client.get("/usage/check")

        assert response.status_code == 200
        data = response.json()
        assert data["threshold"] == "ok"
        assert data["used"] == 500
        assert data["cap"] == 1000

    def test_1_7_int_010_check_missing_org(self, no_org_client):
        response = no_org_client.get("/usage/check")
        assert response.status_code == 403

    def test_1_7_int_011_check_exceeded(self, client):
        with (
            patch.object(
                usage_mod,
                "get_org_plan",
                new_callable=AsyncMock,
                return_value="free",
            ),
            patch.object(
                usage_mod,
                "check_usage_cap",
                new_callable=AsyncMock,
                return_value="exceeded",
            ),
            patch.object(
                usage_mod,
                "get_monthly_usage",
                new_callable=AsyncMock,
                return_value=1000,
            ),
            patch.object(
                usage_mod, "get_monthly_cap", new_callable=AsyncMock, return_value=1000
            ),
        ):
            response = client.get("/usage/check")

        assert response.status_code == 200
        data = response.json()
        assert data["threshold"] == "exceeded"
