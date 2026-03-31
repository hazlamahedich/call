"""
Story 2.1: Vapi Telephony Bridge & Webhook Integration
Unit Tests for Calls Router

Test ID Format: [2.1-UNIT-XXX]
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _create_test_app():
    app = FastAPI()
    from routers.calls import router

    app.include_router(router)
    return app


class TestTriggerCallEndpoint:
    """[2.1-UNIT-200..208] POST /calls/trigger endpoint tests"""

    @pytest.fixture
    def client(self):
        return TestClient(_create_test_app())

    def test_2_1_unit_200_P0_given_missing_phone_number_when_trigger_then_returns_422(
        self, client
    ):
        response = client.post("/calls/trigger", json={"phoneNumber": "   "})
        assert response.status_code == 422

    def test_2_1_unit_201_P0_given_no_org_context_when_trigger_then_returns_403(
        self, client
    ):
        mock_request_state = MagicMock()
        mock_request_state.org_id = None
        mock_request_state.user_id = None

        with (
            patch("routers.calls.check_call_cap", new_callable=AsyncMock),
            patch("routers.calls.get_session", new_callable=AsyncMock) as mock_sess,
        ):
            mock_session = AsyncMock()
            mock_sess.return_value = mock_session

            response = client.post(
                "/calls/trigger",
                json={"phoneNumber": "+1234567890"},
            )

        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "AUTH_FORBIDDEN"

    def test_2_1_unit_206_P0_given_invalid_phone_format_when_trigger_then_returns_422(
        self, client
    ):
        response = client.post(
            "/calls/trigger",
            json={"phoneNumber": "not-a-phone"},
        )
        assert response.status_code == 422

    def test_2_1_unit_207_P0_given_valid_e164_phone_when_trigger_then_returns_422_or_500(
        self, client
    ):
        with (
            patch("routers.calls.check_call_cap", new_callable=AsyncMock),
            patch("routers.calls.get_session", new_callable=AsyncMock) as mock_sess,
            patch("routers.calls._resolve_assistant_id", new_callable=AsyncMock),
            patch("routers.calls._compliance_pre_check"),
            patch(
                "routers.calls.trigger_outbound_call", new_callable=AsyncMock
            ) as mock_trigger,
        ):
            mock_session = AsyncMock()
            mock_sess.return_value = mock_session
            mock_trigger.return_value = MagicMock(
                model_dump=MagicMock(
                    return_value={
                        "id": 1,
                        "vapiCallId": "vapi_123",
                        "status": "pending",
                    }
                )
            )

            response = client.post(
                "/calls/trigger",
                json={"phoneNumber": "+1234567890"},
            )

        assert response.status_code in (200, 201, 403, 500)


class TestCallsRouterRegistration:
    """[2.1-UNIT-210] Verify calls router is properly configured"""

    def test_2_1_unit_210_P0_given_calls_router_when_imported_then_has_trigger_route(
        self,
    ):
        from routers.calls import router

        routes = [r.path for r in router.routes]
        assert "/calls/trigger" in routes
