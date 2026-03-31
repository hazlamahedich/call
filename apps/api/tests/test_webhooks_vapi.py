"""
Story 2.1: Vapi Telephony Bridge & Webhook Integration
Unit Tests for Vapi Webhooks Router

Test ID Format: [2.1-UNIT-XXX]
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from middleware.vapi_auth import verify_vapi_signature
from database.session import get_session
from tests.support.factories import WebhookPayloadFactory


async def _bypass_vapi_sig(request: Request):
    return None


def _create_test_app():
    app = FastAPI()
    from routers.webhooks_vapi import router

    app.include_router(router)
    app.dependency_overrides[verify_vapi_signature] = _bypass_vapi_sig
    mock_session = AsyncMock()

    async def _override_get_session():
        yield mock_session

    app.dependency_overrides[get_session] = _override_get_session
    return app


class TestWebhookCallEvents:
    """[2.1-UNIT-300..308] POST /webhooks/vapi/call-events tests"""

    @pytest.fixture
    def client(self):
        return TestClient(_create_test_app())

    @pytest.fixture
    def factory(self):
        return WebhookPayloadFactory

    def test_2_1_unit_300_P0_given_no_overrides_when_webhook_without_sig_then_returns_401(
        self,
    ):
        app = FastAPI()
        from routers.webhooks_vapi import router

        app.include_router(router)
        client = TestClient(app)
        response = client.post("/webhooks/vapi/call-events", json={})
        assert response.status_code == 401

    def test_2_1_unit_301_P0_given_call_start_when_webhook_then_returns_200(
        self, client, factory
    ):
        payload = factory.call_start()

        with patch(
            "routers.webhooks_vapi.handle_call_started",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ):
            response = client.post(
                "/webhooks/vapi/call-events",
                json=payload,
            )

        assert response.status_code == 200
        assert response.json() == {"received": True}

    def test_2_1_unit_302_P0_given_call_end_when_webhook_then_returns_200(
        self, client, factory
    ):
        payload = factory.call_end()

        with patch(
            "routers.webhooks_vapi.handle_call_ended",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ):
            response = client.post(
                "/webhooks/vapi/call-events",
                json=payload,
            )

        assert response.status_code == 200

    def test_2_1_unit_303_P0_given_call_failed_when_webhook_then_returns_200(
        self, client, factory
    ):
        payload = factory.call_failed()

        with patch(
            "routers.webhooks_vapi.handle_call_failed",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ):
            response = client.post(
                "/webhooks/vapi/call-events",
                json=payload,
            )

        assert response.status_code == 200

    def test_2_1_unit_304_P1_given_missing_call_id_when_webhook_then_returns_200(
        self, client, factory
    ):
        payload = factory.missing_call_id()

        response = client.post(
            "/webhooks/vapi/call-events",
            json=payload,
        )

        assert response.status_code == 200

    def test_2_1_unit_305_P1_given_missing_org_id_when_webhook_then_returns_200(
        self, client, factory
    ):
        payload = factory.missing_org_id(vapi_call_id="vapi_abc")

        response = client.post(
            "/webhooks/vapi/call-events",
            json=payload,
        )

        assert response.status_code == 200

    def test_2_1_unit_306_P1_given_unhandled_event_type_when_webhook_then_returns_200(
        self, client, factory
    ):
        payload = factory.unknown_event()

        response = client.post(
            "/webhooks/vapi/call-events",
            json=payload,
        )

        assert response.status_code == 200

    def test_2_1_unit_307_P0_given_handler_error_when_webhook_then_still_returns_200(
        self, client, factory
    ):
        payload = factory.call_start()

        with patch(
            "routers.webhooks_vapi.handle_call_started",
            new_callable=AsyncMock,
            side_effect=RuntimeError("DB down"),
        ):
            response = client.post(
                "/webhooks/vapi/call-events",
                json=payload,
            )

        assert response.status_code == 200

    def test_2_1_unit_308_P1_given_error_as_string_when_call_failed_then_handles_gracefully(
        self, client, factory
    ):
        payload = factory.call_failed_string_error()

        with patch(
            "routers.webhooks_vapi.handle_call_failed",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ):
            response = client.post(
                "/webhooks/vapi/call-events",
                json=payload,
            )

        assert response.status_code == 200
