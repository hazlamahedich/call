"""
Story 2.1: Vapi Telephony Bridge & Webhook Integration
Unit Tests for Vapi Client (HTTP)

Test ID Format: [2.1-UNIT-XXX]
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx


class TestInitiateCall:
    """[2.1-UNIT-001..007] Vapi client HTTP integration tests"""

    @pytest.mark.asyncio
    async def test_2_1_unit_001_P0_given_valid_response_when_initiate_call_then_returns_json(
        self,
    ):
        from services.vapi_client import initiate_call

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"id": "call_abc123"}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("services.vapi_client.httpx.AsyncClient", return_value=mock_client):
            result = await initiate_call(
                phone_number="+1234567890",
                assistant_id="asst_123",
                metadata={"org_id": "org_abc"},
            )

        assert result == {"id": "call_abc123"}
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_2_1_unit_002_P0_given_4xx_error_when_initiate_call_then_raises_immediately(
        self,
    ):
        from services.vapi_client import initiate_call

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Request",
            request=MagicMock(),
            response=mock_response,
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("services.vapi_client.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(httpx.HTTPStatusError):
                await initiate_call(
                    phone_number="+1234567890",
                    assistant_id="asst_123",
                )

    @pytest.mark.asyncio
    async def test_2_1_unit_003_P1_given_5xx_error_when_initiate_call_then_retries(
        self,
    ):
        from services.vapi_client import initiate_call

        mock_500_response = MagicMock()
        mock_500_response.status_code = 500
        mock_500_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error",
            request=MagicMock(),
            response=mock_500_response,
        )

        mock_ok_response = MagicMock()
        mock_ok_response.status_code = 200
        mock_ok_response.raise_for_status = MagicMock()
        mock_ok_response.json.return_value = {"id": "call_retry_ok"}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[mock_500_response, mock_ok_response])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("services.vapi_client.httpx.AsyncClient", return_value=mock_client),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            result = await initiate_call(
                phone_number="+1234567890",
                assistant_id="asst_123",
            )

        assert result == {"id": "call_retry_ok"}
        assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_2_1_unit_004_P0_given_timeout_when_initiate_call_then_retries_and_raises(
        self,
    ):
        from services.vapi_client import initiate_call, _RETRY_ATTEMPTS

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=httpx.TimeoutException("Connection timed out")
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("services.vapi_client.httpx.AsyncClient", return_value=mock_client),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            with pytest.raises(RuntimeError, match="Vapi API call failed"):
                await initiate_call(
                    phone_number="+1234567890",
                    assistant_id="asst_123",
                )

        assert mock_client.post.call_count == _RETRY_ATTEMPTS

    @pytest.mark.asyncio
    async def test_2_1_unit_005_P1_given_no_metadata_when_initiate_call_then_payload_has_no_metadata(
        self,
    ):
        from services.vapi_client import initiate_call

        captured_payload = {}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"id": "call_xyz"}

        async def capture_post(url, json=None, headers=None):
            captured_payload.update(json or {})
            return mock_response

        mock_client = AsyncMock()
        mock_client.post = capture_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("services.vapi_client.httpx.AsyncClient", return_value=mock_client):
            await initiate_call(phone_number="+1234567890", assistant_id="asst_123")

        assert "metadata" not in captured_payload
        assert captured_payload["phoneNumber"] == "+1234567890"
        assert captured_payload["assistantId"] == "asst_123"

    @pytest.mark.asyncio
    async def test_2_1_unit_006_P1_given_metadata_when_initiate_call_then_payload_includes_metadata(
        self,
    ):
        from services.vapi_client import initiate_call

        captured_payload = {}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"id": "call_meta"}

        async def capture_post(url, json=None, headers=None):
            captured_payload.update(json or {})
            return mock_response

        mock_client = AsyncMock()
        mock_client.post = capture_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("services.vapi_client.httpx.AsyncClient", return_value=mock_client):
            await initiate_call(
                phone_number="+1234567890",
                assistant_id="asst_123",
                metadata={"org_id": "org_abc", "lead_id": "42"},
            )

        assert captured_payload["metadata"] == {"org_id": "org_abc", "lead_id": "42"}

    @pytest.mark.asyncio
    async def test_2_1_unit_007_P0_given_auth_header_when_initiate_call_then_uses_bearer_token(
        self,
    ):
        from services.vapi_client import initiate_call

        captured_headers = {}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"id": "call_auth"}

        async def capture_post(url, json=None, headers=None):
            captured_headers.update(headers or {})
            return mock_response

        mock_client = AsyncMock()
        mock_client.post = capture_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("services.vapi_client.httpx.AsyncClient", return_value=mock_client),
            patch("services.vapi_client.settings") as mock_settings,
        ):
            mock_settings.VAPI_API_KEY = "test-key-123"
            mock_settings.VAPI_BASE_URL = "https://api.vapi.ai"
            await initiate_call(phone_number="+1234567890", assistant_id="asst_123")

        assert captured_headers["Authorization"] == "Bearer test-key-123"
