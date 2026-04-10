"""[4.1-EXP] DncComProvider — mock mode, retry, error handling, health, close"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_exp_com_provider_mock_mode():
    # Given: DncComProvider with no API key (mock mode)
    # When: lookup is called
    # Then: returns clear result from mock_provider
    from services.compliance.dnc_com_provider import DncComProvider

    provider = DncComProvider()
    with patch("services.compliance.dnc_com_provider.settings") as mock_settings:
        mock_settings.DNC_API_KEY = ""
        mock_settings.DNC_API_BASE_URL = "https://api.dnc.com"
        mock_settings.DNC_PRE_DIAL_TIMEOUT_MS = 100
        result = await provider.lookup("+12025551234")
    assert result.result == "clear"
    assert result.is_blocked is False
    assert result.source == "mock_provider"


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_exp_com_provider_mock_health():
    from services.compliance.dnc_com_provider import DncComProvider

    provider = DncComProvider()
    with patch("services.compliance.dnc_com_provider.settings") as mock_settings:
        mock_settings.DNC_API_KEY = ""
        mock_settings.DNC_API_BASE_URL = "https://api.dnc.com"
        health = await provider.health_check()
    assert health is True


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_exp_com_provider_rate_limited_then_success():
    # Given: provider returns 429 then 200
    # When: lookup is called
    # Then: retries and returns clear result
    from services.compliance.dnc_com_provider import DncComProvider

    provider = DncComProvider()
    mock_resp_429 = MagicMock()
    mock_resp_429.status_code = 429
    mock_resp_429.headers = {"Retry-After": "0.01"}
    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = {"status": "clear", "source": "dnc_com"}
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=[mock_resp_429, mock_resp_200])
    mock_client.is_closed = False

    with (
        patch("services.compliance.dnc_com_provider.settings") as mock_settings,
        patch.object(provider, "_ensure_client", return_value=mock_client),
    ):
        mock_settings.DNC_API_KEY = "test-key"
        result = await provider.lookup("+12025551234")
    assert result.result == "clear"


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_exp_com_provider_500_exhaustion():
    # Given: provider always returns 503
    # When: lookup is called
    # Then: exhausts retries and returns error
    from services.compliance.dnc_com_provider import DncComProvider

    provider = DncComProvider()
    mock_resp = MagicMock()
    mock_resp.status_code = 503
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.is_closed = False

    with (
        patch("services.compliance.dnc_com_provider.settings") as mock_settings,
        patch.object(provider, "_ensure_client", return_value=mock_client),
        patch(
            "services.compliance.dnc_com_provider.asyncio.sleep", new_callable=AsyncMock
        ),
    ):
        mock_settings.DNC_API_KEY = "test-key"
        result = await provider.lookup("+12025551234")
    assert result.result == "error"
    assert mock_client.post.call_count == 3


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_exp_com_provider_timeout():
    import httpx
    from services.compliance.dnc_com_provider import DncComProvider

    provider = DncComProvider()
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
    mock_client.is_closed = False

    with (
        patch("services.compliance.dnc_com_provider.settings") as mock_settings,
        patch.object(provider, "_ensure_client", return_value=mock_client),
        patch(
            "services.compliance.dnc_com_provider.asyncio.sleep", new_callable=AsyncMock
        ),
    ):
        mock_settings.DNC_API_KEY = "test-key"
        result = await provider.lookup("+12025551234")
    assert result.result == "error"


@pytest.mark.asyncio
@pytest.mark.p1
async def test_4_1_exp_com_provider_blocked_response():
    from services.compliance.dnc_com_provider import DncComProvider

    provider = DncComProvider()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"status": "blocked", "source": "national_dnc"}
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.is_closed = False

    with (
        patch("services.compliance.dnc_com_provider.settings") as mock_settings,
        patch.object(provider, "_ensure_client", return_value=mock_client),
    ):
        mock_settings.DNC_API_KEY = "test-key"
        result = await provider.lookup("+12025551234")
    assert result.is_blocked is True
    assert result.result == "blocked"
    assert result.source == "national_dnc"


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_exp_com_provider_malformed_json():
    from services.compliance.dnc_com_provider import DncComProvider

    provider = DncComProvider()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.side_effect = ValueError("bad json")
    mock_resp.text = "not json"
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.is_closed = False

    with (
        patch("services.compliance.dnc_com_provider.settings") as mock_settings,
        patch.object(provider, "_ensure_client", return_value=mock_client),
    ):
        mock_settings.DNC_API_KEY = "test-key"
        result = await provider.lookup("+12025551234")
    assert result.result == "error"
    assert result.raw_response is not None


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_exp_com_provider_health_check_failure():
    from services.compliance.dnc_com_provider import DncComProvider

    provider = DncComProvider()
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.is_closed = False

    with (
        patch("services.compliance.dnc_com_provider.settings") as mock_settings,
        patch.object(provider, "_ensure_client", return_value=mock_client),
    ):
        mock_settings.DNC_API_KEY = "test-key"
        health = await provider.health_check()
    assert health is False


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_exp_com_provider_health_check_exception():
    from services.compliance.dnc_com_provider import DncComProvider

    provider = DncComProvider()
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=Exception("network error"))
    mock_client.is_closed = False

    with (
        patch("services.compliance.dnc_com_provider.settings") as mock_settings,
        patch.object(provider, "_ensure_client", return_value=mock_client),
    ):
        mock_settings.DNC_API_KEY = "test-key"
        health = await provider.health_check()
    assert health is False


@pytest.mark.asyncio
@pytest.mark.p3
async def test_4_1_exp_com_provider_close():
    from services.compliance.dnc_com_provider import DncComProvider

    provider = DncComProvider()
    mock_client = AsyncMock()
    mock_client.is_closed = False
    mock_client.aclose = AsyncMock()
    provider._client = mock_client
    await provider.close()
    mock_client.aclose.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.p3
async def test_4_1_exp_com_provider_close_already_closed():
    from services.compliance.dnc_com_provider import DncComProvider

    provider = DncComProvider()
    mock_client = AsyncMock()
    mock_client.is_closed = True
    provider._client = mock_client
    await provider.close()
    mock_client.aclose.assert_not_called()


@pytest.mark.p3
def test_4_1_exp_safe_retry_after_none():
    from services.compliance.dnc_com_provider import _safe_retry_after

    assert _safe_retry_after(None) == 0.5


@pytest.mark.p3
def test_4_1_exp_safe_retry_after_float():
    from services.compliance.dnc_com_provider import _safe_retry_after

    assert _safe_retry_after("2.5") == 2.5


@pytest.mark.p3
def test_4_1_exp_safe_retry_after_invalid():
    from services.compliance.dnc_com_provider import _safe_retry_after

    assert _safe_retry_after("not-a-number") == 0.5


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_exp_com_provider_connect_error():
    import httpx
    from services.compliance.dnc_com_provider import DncComProvider

    provider = DncComProvider()
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
    mock_client.is_closed = False

    with (
        patch("services.compliance.dnc_com_provider.settings") as mock_settings,
        patch.object(provider, "_ensure_client", return_value=mock_client),
        patch(
            "services.compliance.dnc_com_provider.asyncio.sleep", new_callable=AsyncMock
        ),
    ):
        mock_settings.DNC_API_KEY = "test-key"
        result = await provider.lookup("+12025551234")
    assert result.result == "error"
