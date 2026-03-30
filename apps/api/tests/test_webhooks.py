import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import json

from routers.webhooks import router


@pytest.fixture
def app():
    application = FastAPI()
    application.include_router(router)
    return application


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def valid_webhook_payload():
    return {
        "type": "organization.created",
        "data": {
            "id": "org_123456",
            "name": "Test Agency",
            "slug": "test-agency",
            "public_metadata": {"type": "agency", "plan": "pro", "clients": []},
        },
    }


@pytest.fixture
def membership_created_payload():
    return {
        "type": "organizationMembership.created",
        "data": {
            "id": "mem_123456",
            "organization": {"id": "org_123456"},
            "public_user_data": {"user_id": "user_123456"},
            "role": "org:admin",
        },
    }


class TestWebhookReceiver:
    def test_webhook_missing_secret_returns_500(self, client):
        payload = {"type": "test", "data": {}}
        response = client.post(
            "/webhooks/clerk",
            json=payload,
        )
        assert response.status_code == 500

    @patch("routers.webhooks.settings.CLERK_WEBHOOK_SECRET", "whsec_test_secret")
    @patch("svix.webhooks.Webhook.verify")
    @patch("routers.webhooks.handle_organization_created", new_callable=AsyncMock)
    def test_valid_organization_created_webhook(
        self, mock_handler, mock_verify, client, valid_webhook_payload
    ):
        mock_verify.return_value = valid_webhook_payload

        response = client.post(
            "/webhooks/clerk",
            json=valid_webhook_payload,
            headers={"svix-id": "msg_123", "svix-signature": "valid_sig"},
        )

        assert response.status_code == 200
        assert response.json() == {"received": True}
        mock_handler.assert_called_once()

    @patch("routers.webhooks.settings.CLERK_WEBHOOK_SECRET", "whsec_test_secret")
    @patch("svix.webhooks.Webhook.verify")
    def test_membership_created_webhook(
        self, mock_verify, client, membership_created_payload
    ):
        mock_verify.return_value = membership_created_payload

        response = client.post(
            "/webhooks/clerk",
            json=membership_created_payload,
            headers={"svix-id": "msg_124", "svix-signature": "valid_sig"},
        )

        assert response.status_code == 200
        assert response.json() == {"received": True}

    @patch("routers.webhooks.settings.CLERK_WEBHOOK_SECRET", "whsec_test_secret")
    @patch("svix.webhooks.Webhook.verify")
    @patch("routers.webhooks.handle_organization_updated", new_callable=AsyncMock)
    def test_organization_updated_webhook(self, mock_handler, mock_verify, client):
        payload = {
            "type": "organization.updated",
            "data": {"id": "org_123456", "name": "Updated Agency Name"},
        }
        mock_verify.return_value = payload

        response = client.post(
            "/webhooks/clerk",
            json=payload,
            headers={"svix-id": "msg_125", "svix-signature": "valid_sig"},
        )

        assert response.status_code == 200
        mock_handler.assert_called_once()

    @patch("routers.webhooks.settings.CLERK_WEBHOOK_SECRET", "whsec_test_secret")
    @patch("svix.webhooks.Webhook.verify")
    @patch("routers.webhooks.handle_organization_deleted", new_callable=AsyncMock)
    def test_organization_deleted_webhook(self, mock_handler, mock_verify, client):
        payload = {"type": "organization.deleted", "data": {"id": "org_123456"}}
        mock_verify.return_value = payload

        response = client.post(
            "/webhooks/clerk",
            json=payload,
            headers={"svix-id": "msg_126", "svix-signature": "valid_sig"},
        )

        assert response.status_code == 200
        mock_handler.assert_called_once()

    @patch("routers.webhooks.settings.CLERK_WEBHOOK_SECRET", "whsec_test_secret")
    @patch("svix.webhooks.Webhook.verify")
    def test_unhandled_event_type(self, mock_verify, client):
        payload = {"type": "user.created", "data": {"id": "user_123456"}}
        mock_verify.return_value = payload

        response = client.post(
            "/webhooks/clerk",
            json=payload,
            headers={"svix-id": "msg_127", "svix-signature": "valid_sig"},
        )

        assert response.status_code == 200
        assert response.json() == {"received": True}

    @patch("routers.webhooks.settings.CLERK_WEBHOOK_SECRET", "whsec_test_secret")
    @patch("svix.webhooks.Webhook.verify")
    def test_invalid_webhook_signature(
        self, mock_verify, client, valid_webhook_payload
    ):
        from svix.exceptions import WebhookVerificationError

        mock_verify.side_effect = WebhookVerificationError("Invalid signature")

        response = client.post(
            "/webhooks/clerk",
            json=valid_webhook_payload,
            headers={"svix-id": "msg_128", "svix-signature": "invalid_sig"},
        )

        assert response.status_code == 401

    @patch("routers.webhooks.settings.CLERK_WEBHOOK_SECRET", "whsec_test_secret")
    @patch("svix.webhooks.Webhook.verify")
    @patch("routers.webhooks.handle_organization_created", new_callable=AsyncMock)
    def test_idempotent_webhook_handling(
        self, mock_handler, mock_verify, client, valid_webhook_payload
    ):
        mock_verify.return_value = valid_webhook_payload

        response1 = client.post(
            "/webhooks/clerk",
            json=valid_webhook_payload,
            headers={"svix-id": "msg_129", "svix-signature": "valid_sig"},
        )

        response2 = client.post(
            "/webhooks/clerk",
            json=valid_webhook_payload,
            headers={"svix-id": "msg_129", "svix-signature": "valid_sig"},
        )

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.json() == {"received": True}
        assert response2.json() == {"received": True}

    @patch("routers.webhooks.settings.CLERK_WEBHOOK_SECRET", "whsec_test_secret")
    @patch("svix.webhooks.Webhook.verify")
    def test_membership_updated_webhook(self, mock_verify, client):
        payload = {
            "type": "organizationMembership.updated",
            "data": {
                "id": "mem_789",
                "organization": {"id": "org_123456"},
                "public_user_data": {"user_id": "user_123456"},
                "role": "org:member",
            },
        }
        mock_verify.return_value = payload

        response = client.post(
            "/webhooks/clerk",
            json=payload,
            headers={"svix-id": "msg_130", "svix-signature": "valid_sig"},
        )

        assert response.status_code == 200
        assert response.json() == {"received": True}

    @patch("routers.webhooks.settings.CLERK_WEBHOOK_SECRET", "whsec_test_secret")
    @patch("svix.webhooks.Webhook.verify")
    def test_membership_deleted_webhook(self, mock_verify, client):
        payload = {
            "type": "organizationMembership.deleted",
            "data": {
                "id": "mem_999",
                "organization": {"id": "org_123456"},
                "public_user_data": {"user_id": "user_123456"},
            },
        }
        mock_verify.return_value = payload

        response = client.post(
            "/webhooks/clerk",
            json=payload,
            headers={"svix-id": "msg_131", "svix-signature": "valid_sig"},
        )

        assert response.status_code == 200
        assert response.json() == {"received": True}
