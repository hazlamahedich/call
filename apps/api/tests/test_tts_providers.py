"""
[2.3-UNIT-001] Test TTS provider clients — ElevenLabs and Cartesia.

Covers: successful synthesis, timeout handling, auth errors, rate limits,
latency measurement accuracy, error flag on TTSResponse for failures.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.tts.base import TTSResponse
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


def _make_timeout_error():
    import httpx

    return httpx.TimeoutException("read timeout")


@pytest.fixture
def elevenlabs_provider():
    return ElevenLabsProvider()


@pytest.fixture
def cartesia_provider():
    return CartesiaProvider()


class TestElevenLabsProviderSynthesis:
    """
    [2.3-UNIT-001_P0] Given ElevenLabs provider, when synthesize is called,
    then it returns audio bytes and measures latency.
    """

    @pytest.mark.asyncio
    async def test_successful_synthesis_returns_audio(self, elevenlabs_provider):
        with patch.object(
            elevenlabs_provider._client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = _make_httpx_response(200, b"mp3-audio-bytes")

            response = await elevenlabs_provider.synthesize("Hello", "voice-123")

            assert isinstance(response, TTSResponse)
            assert response.audio_bytes == b"mp3-audio-bytes"
            assert response.provider == "elevenlabs"
            assert response.error is False
            assert response.latency_ms > 0

    @pytest.mark.asyncio
    async def test_successful_synthesis_sends_correct_request(
        self, elevenlabs_provider
    ):
        with patch.object(
            elevenlabs_provider._client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = _make_httpx_response(200, b"audio")

            await elevenlabs_provider.synthesize(
                "Hello world", "voice-abc", model="eleven_turbo_v2"
            )

            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "voice-abc" in call_args[1].get(
                "url", call_args[0][0] if call_args[0] else ""
            )
            body = call_args[1].get("json", {})
            assert body["text"] == "Hello world"
            assert body["model_id"] == "eleven_turbo_v2"

    @pytest.mark.asyncio
    async def test_timeout_returns_error_response(self, elevenlabs_provider):
        with patch.object(
            elevenlabs_provider._client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.side_effect = _make_timeout_error()

            response = await elevenlabs_provider.synthesize("Hello", "voice-123")

            assert response.error is True
            assert response.audio_bytes == b""
            assert response.error_message == "Timeout"
            assert response.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_auth_error_401_returns_error(self, elevenlabs_provider):
        with patch.object(
            elevenlabs_provider._client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = _make_httpx_response(401)

            response = await elevenlabs_provider.synthesize("Hello", "voice-123")

            assert response.error is True
            assert "401" in response.error_message

    @pytest.mark.asyncio
    async def test_auth_error_403_returns_error(self, elevenlabs_provider):
        with patch.object(
            elevenlabs_provider._client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = _make_httpx_response(403)

            response = await elevenlabs_provider.synthesize("Hello", "voice-123")

            assert response.error is True
            assert "403" in response.error_message

    @pytest.mark.asyncio
    async def test_rate_limit_429_returns_error(self, elevenlabs_provider):
        with patch.object(
            elevenlabs_provider._client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = _make_httpx_response(429)

            response = await elevenlabs_provider.synthesize("Hello", "voice-123")

            assert response.error is True
            assert "Rate limited" in response.error_message

    @pytest.mark.asyncio
    async def test_provider_name(self, elevenlabs_provider):
        assert elevenlabs_provider.provider_name == "elevenlabs"

    @pytest.mark.asyncio
    async def test_uses_default_model_when_none(self, elevenlabs_provider):
        with patch.object(
            elevenlabs_provider._client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = _make_httpx_response(200, b"audio")

            await elevenlabs_provider.synthesize("Hello", "v1", model=None)

            body = mock_post.call_args[1]["json"]
            assert body["model_id"] == "eleven_multilingual_v2"


class TestElevenLabsHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_returns_true_on_200(self, elevenlabs_provider):
        with patch("services.tts.elevenlabs.settings.ELEVENLABS_API_KEY", "test-key"):
            with patch.object(
                elevenlabs_provider._client, "get", new_callable=AsyncMock
            ) as mock_get:
                mock_get.return_value = _make_httpx_response(200)
                result = await elevenlabs_provider.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_returns_false_on_error(self, elevenlabs_provider):
        with patch("services.tts.elevenlabs.settings.ELEVENLABS_API_KEY", "test-key"):
            with patch.object(
                elevenlabs_provider._client, "get", new_callable=AsyncMock
            ) as mock_get:
                mock_get.return_value = _make_httpx_response(500)
                result = await elevenlabs_provider.health_check()
            assert result is False


class TestCartesiaProviderSynthesis:
    """
    [2.3-UNIT-001_P0] Given Cartesia provider, when synthesize is called,
    then it returns audio bytes and measures latency.
    """

    @pytest.mark.asyncio
    async def test_successful_synthesis_returns_audio(self, cartesia_provider):
        with patch.object(
            cartesia_provider._client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = _make_httpx_response(200, b"mp3-bytes")

            response = await cartesia_provider.synthesize("Hello", "voice-456")

            assert isinstance(response, TTSResponse)
            assert response.audio_bytes == b"mp3-bytes"
            assert response.provider == "cartesia"
            assert response.error is False

    @pytest.mark.asyncio
    async def test_sends_correct_cartesia_payload(self, cartesia_provider):
        with patch.object(
            cartesia_provider._client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = _make_httpx_response(200, b"audio")

            await cartesia_provider.synthesize("Test", "v-789", model="sonic-english")

            body = mock_post.call_args[1]["json"]
            assert body["transcript"] == "Test"
            assert body["voice"]["id"] == "v-789"
            assert body["model_id"] == "sonic-english"

    @pytest.mark.asyncio
    async def test_timeout_returns_error_response(self, cartesia_provider):
        with patch.object(
            cartesia_provider._client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.side_effect = _make_timeout_error()

            response = await cartesia_provider.synthesize("Hello", "voice-123")

            assert response.error is True
            assert response.error_message == "Timeout"

    @pytest.mark.asyncio
    async def test_rate_limit_returns_error(self, cartesia_provider):
        with patch.object(
            cartesia_provider._client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = _make_httpx_response(429)

            response = await cartesia_provider.synthesize("Hello", "voice-123")

            assert response.error is True
            assert "Rate limited" in response.error_message

    @pytest.mark.asyncio
    async def test_provider_name(self, cartesia_provider):
        assert cartesia_provider.provider_name == "cartesia"

    @pytest.mark.asyncio
    async def test_uses_default_model_when_none(self, cartesia_provider):
        with patch.object(
            cartesia_provider._client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = _make_httpx_response(200, b"audio")

            await cartesia_provider.synthesize("Hello", "v1", model=None)

            body = mock_post.call_args[1]["json"]
            assert body["model_id"] == "sonic-english"


class TestCartesiaHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_returns_true_when_key_configured(
        self, cartesia_provider
    ):
        with patch("services.tts.cartesia.settings") as mock_settings:
            mock_settings.CARTESIA_API_KEY = "test-key"
            result = await cartesia_provider.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_returns_false_when_no_key(self, cartesia_provider):
        with patch("services.tts.cartesia.settings") as mock_settings:
            mock_settings.CARTESIA_API_KEY = ""
            result = await cartesia_provider.health_check()
            assert result is False
