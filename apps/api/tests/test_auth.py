"""
Story 1-2: Multi-layer Hierarchy & Clerk Auth Integration
API Unit Tests for Auth Middleware

Test ID Format: 1.2-API-XXX
Priority: P0 (Critical) | P1 (High) | P2 (Medium) | P3 (Low)
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from middleware.auth import AuthMiddleware
import json
import jwt


@pytest.fixture
def app():
    application = FastAPI()
    application.add_middleware(AuthMiddleware, jwks_url="https://test.jwks.url")

    @application.get("/protected")
    async def protected_route():
        return {"message": "success"}

    @application.get("/health")
    async def health_route():
        return {"status": "healthy"}

    return application


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def mock_jwks():
    return {
        "keys": [
            {
                "kid": "test-kid",
                "kty": "RSA",
                "use": "sig",
                "n": "test-n",
                "e": "AQAB",
            }
        ]
    }


class TestAuthMiddleware:
    """[P0] Tests for AuthMiddleware JWT validation - AC4"""

    def test_1_2_api_010_missing_authorization_header(self, client):
        # Given: Request to protected endpoint without Authorization header
        # When: Request is made
        response = client.get("/protected")
        # Then: Should return 401 with AUTH_INVALID_TOKEN code
        assert response.status_code == 401
        data = response.json()
        assert data["code"] == "AUTH_INVALID_TOKEN"
        assert "Missing" in data["message"] or "invalid" in data["message"]

    def test_1_2_api_011_invalid_authorization_format(self, client):
        # Given: Request with malformed Authorization header
        # When: Request is made
        response = client.get("/protected", headers={"Authorization": "InvalidFormat"})
        # Then: Should return 401 with AUTH_INVALID_TOKEN code
        assert response.status_code == 401
        data = response.json()
        assert data["code"] == "AUTH_INVALID_TOKEN"

    def test_1_2_api_012_skip_auth_for_health(self, client):
        # Given: Request to health endpoint (public)
        # When: Request is made without auth
        response = client.get("/health")
        # Then: Should return 200 (auth skipped)
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    @patch("middleware.auth.PyJWKClient")
    def test_1_2_api_013_valid_token_extraction(self, mock_jwk_client, client):
        # Given: Valid JWT token with user and org claims
        mock_payload = {"sub": "user_123", "org_id": "org_456"}
        mock_signing_key = MagicMock()
        mock_signing_key.key = "mock_key"
        mock_jwk_client.get_signing_key_from_jwt.return_value = mock_signing_key
        # When: Request is made with valid Bearer token
        with patch("jwt.decode", return_value=mock_payload):
            response = client.get(
                "/protected",
                headers={"Authorization": "Bearer valid.token.here"},
            )
        # Then: Should return 200 with protected content
        assert response.status_code == 200
        assert response.json() == {"message": "success"}

    @patch("middleware.auth.PyJWKClient")
    def test_1_2_api_014_expired_token(self, mock_jwk_client, client):
        # Given: Expired JWT token
        mock_signing_key = MagicMock()
        mock_jwk_client.get_signing_key_from_jwt.return_value = mock_signing_key
        # When: Request is made with expired token
        with patch("jwt.decode", side_effect=jwt.ExpiredSignatureError()):
            response = client.get(
                "/protected",
                headers={"Authorization": "Bearer expired.token.here"},
            )
        # Then: Should return 401 with AUTH_TOKEN_EXPIRED code
        assert response.status_code == 401
        data = response.json()
        assert data["code"] == "AUTH_TOKEN_EXPIRED"

    @patch("middleware.auth.PyJWKClient")
    def test_1_2_api_015_malformed_token(self, mock_jwk_client, client):
        # Given: Malformed JWT token
        mock_signing_key = MagicMock()
        mock_jwk_client.get_signing_key_from_jwt.return_value = mock_signing_key
        # When: Request is made with malformed token
        with patch("jwt.decode", side_effect=jwt.InvalidTokenError("Invalid")):
            response = client.get(
                "/protected",
                headers={"Authorization": "Bearer malformed.token.here"},
            )
        # Then: Should return 401 with AUTH_INVALID_TOKEN code
        assert response.status_code == 401
        data = response.json()
        assert data["code"] == "AUTH_INVALID_TOKEN"
