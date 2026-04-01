"""
[2.3-UNIT-014] Test TTS provider edge cases — Cartesia auth errors,
ElevenLabs health_check no key, content-type defaults, aclose lifecycle.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.tts.elevenlabs import ElevenLabsProvider
from services.tts.cartesia import CartesiaProvider


def _make_httpx_response(
    status_code: int = 200, content: bytes = b"audio-data", headers: dict | None = None
):
    resp = MagicMock()
    resp.status_code = status_code
    resp.content = content
    resp.headers = headers or {"content-type": "audio/mpeg"}
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


@pytest.fixture
def elevenlabs_provider():
    return ElevenLabsProvider()


@pytest.fixture
def cartesia_provider():
    return CartesiaProvider()


class TestCartesiaAuthErrors:
    """
    [2.3-UNIT-014_P1] Cartesia 401/403 auth error handling.
    """

    @pytest.mark.asyncio
    async def test_P1_auth_error_401_returns_error(self, cartesia_provider):
        with patch.object(
            cartesia_provider._client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = _make_httpx_response(401)

            response = await cartesia_provider.synthesize("Hello", "voice-123")

            assert response.error is True
            assert "401" in response.error_message

    @pytest.mark.asyncio
    async def test_P1_auth_error_403_returns_error(self, cartesia_provider):
        with patch.object(
            cartesia_provider._client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = _make_httpx_response(403)

            response = await cartesia_provider.synthesize("Hello", "voice-123")

            assert response.error is True
            assert "403" in response.error_message


class TestElevenLabsHealthCheckNoKey:
    """
    [2.3-UNIT-014_P1] ElevenLabs health_check with empty API key.
    """

    @pytest.mark.asyncio
    async def test_P1_health_check_returns_false_when_no_api_key(
        self, elevenlabs_provider
    ):
        with patch("services.tts.elevenlabs.settings.ELEVENLABS_API_KEY", ""):
            result = await elevenlabs_provider.health_check()
            assert result is False


class TestContentTypeDefault:
    """
    [2.3-UNIT-014_P2] Content-type header defaults when missing from response.
    """

    @pytest.mark.asyncio
    async def test_P2_elevenlabs_uses_default_content_type_when_missing(
        self, elevenlabs_provider
    ):
        with patch.object(
            elevenlabs_provider._client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = _make_httpx_response(200, b"audio", headers={})

            response = await elevenlabs_provider.synthesize("Hello", "v1")

            assert response.content_type == "audio/mpeg"

    @pytest.mark.asyncio
    async def test_P2_cartesia_uses_default_content_type_when_missing(
        self, cartesia_provider
    ):
        with patch.object(
            cartesia_provider._client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = _make_httpx_response(200, b"audio", headers={})

            response = await cartesia_provider.synthesize("Hello", "v1")

            assert response.content_type == "audio/mpeg"


class TestProviderAclose:
    """
    [2.3-UNIT-014_P1] Provider aclose lifecycle.
    """

    @pytest.mark.asyncio
    async def test_P1_elevenlabs_aclose_closes_client(self, elevenlabs_provider):
        with patch.object(
            elevenlabs_provider._client, "aclose", new_callable=AsyncMock
        ) as mock_aclose:
            await elevenlabs_provider.aclose()
            mock_aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_P1_cartesia_aclose_closes_client(self, cartesia_provider):
        with patch.object(
            cartesia_provider._client, "aclose", new_callable=AsyncMock
        ) as mock_aclose:
            await cartesia_provider.aclose()
            mock_aclose.assert_called_once()


class TestProviderEmptyAudioResponse:
    """
    [2.3-UNIT-014_P2] Provider returns 200 with zero bytes.
    """

    @pytest.mark.asyncio
    async def test_P2_elevenlabs_empty_audio_treated_as_success(
        self, elevenlabs_provider
    ):
        with patch.object(
            elevenlabs_provider._client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = _make_httpx_response(200, b"")

            response = await elevenlabs_provider.synthesize("Hello", "v1")

            assert response.error is False
            assert response.audio_bytes == b""

    @pytest.mark.asyncio
    async def test_P2_cartesia_empty_audio_treated_as_success(self, cartesia_provider):
        with patch.object(
            cartesia_provider._client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = _make_httpx_response(200, b"")

            response = await cartesia_provider.synthesize("Hello", "v1")

            assert response.error is False
            assert response.audio_bytes == b""
