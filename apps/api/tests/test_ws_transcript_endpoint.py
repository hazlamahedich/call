"""
Story 2.2: Real-time Audio Stream & Transcription Pipeline
WebSocket Endpoint Integration Tests — Auth, ownership, lifecycle

Test ID Format: [2.2-UNIT-XXX]
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, WebSocketDisconnect
from fastapi.testclient import TestClient

from services.ws_manager import ConnectionManager


def _create_ws_test_app():
    app = FastAPI()
    from routers.ws_transcript import router

    app.include_router(router)
    return app


class TestWSEndpointAuth:
    """[2.2-UNIT-407..412] WebSocket endpoint auth & ownership tests"""

    @pytest.fixture
    def app(self):
        return _create_ws_test_app()

    @pytest.fixture
    def client(self, app):
        return TestClient(app)

    def test_2_2_unit_407_P0_given_no_auth_token_when_ws_connect_then_closes_1008(
        self, client
    ):
        with patch(
            "routers.ws_transcript._receive_auth_token",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with pytest.raises(WebSocketDisconnect) as exc_info:
                with client.websocket_connect("/ws/calls/1/transcript") as ws:
                    ws.receive_json()
            assert exc_info.value.code == 1008

    def test_2_2_unit_408_P0_given_invalid_token_when_ws_connect_then_closes_1008(
        self,
        client,
    ):
        with (
            patch(
                "routers.ws_transcript._receive_auth_token",
                new_callable=AsyncMock,
                return_value="bad-token",
            ),
            patch(
                "routers.ws_transcript._validate_ws_token",
                return_value=None,
            ),
        ):
            with pytest.raises(WebSocketDisconnect) as exc_info:
                with client.websocket_connect("/ws/calls/1/transcript") as ws:
                    ws.receive_json()
            assert exc_info.value.code == 1008

    def test_2_2_unit_409_P0_given_valid_token_no_org_id_when_ws_connect_then_closes_1008(
        self,
        client,
    ):
        with (
            patch(
                "routers.ws_transcript._receive_auth_token",
                new_callable=AsyncMock,
                return_value="valid-token",
            ),
            patch(
                "routers.ws_transcript._validate_ws_token",
                return_value={"sub": "user_1"},
            ),
        ):
            with pytest.raises(WebSocketDisconnect) as exc_info:
                with client.websocket_connect("/ws/calls/1/transcript") as ws:
                    ws.receive_json()
            assert exc_info.value.code == 1008

    def test_2_2_unit_410_P0_given_valid_token_call_not_found_when_ws_connect_then_closes_1008(
        self,
        client,
    ):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.first.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        async def _mock_get_session():
            yield mock_session

        with (
            patch(
                "routers.ws_transcript._receive_auth_token",
                new_callable=AsyncMock,
                return_value="valid-token",
            ),
            patch(
                "routers.ws_transcript._validate_ws_token",
                return_value={"sub": "user_1", "org_id": "org_1"},
            ),
            patch(
                "routers.ws_transcript.get_session",
                _mock_get_session,
            ),
        ):
            with pytest.raises(WebSocketDisconnect) as exc_info:
                with client.websocket_connect("/ws/calls/999/transcript") as ws:
                    ws.receive_json()
            assert exc_info.value.code == 1008

    def test_2_2_unit_411_P0_given_valid_auth_and_ownership_when_ws_connect_then_sends_connected(
        self,
        client,
    ):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.first.return_value = ("org_1",)
        mock_session.execute = AsyncMock(return_value=mock_result)

        async def _mock_get_session():
            yield mock_session

        mock_manager = ConnectionManager()

        with (
            patch(
                "routers.ws_transcript._receive_auth_token",
                new_callable=AsyncMock,
                return_value="valid-token",
            ),
            patch(
                "routers.ws_transcript._validate_ws_token",
                return_value={"sub": "user_1", "org_id": "org_1"},
            ),
            patch(
                "routers.ws_transcript.get_session",
                _mock_get_session,
            ),
            patch("routers.ws_transcript.manager", mock_manager),
        ):
            with client.websocket_connect("/ws/calls/1/transcript") as ws:
                data = ws.receive_json()
                assert data["type"] == "connected"
                assert data["callId"] == 1

    def test_2_2_unit_412_P1_given_connected_ws_when_disconnect_then_manager_cleans_up(
        self,
        client,
    ):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.first.return_value = ("org_1",)
        mock_session.execute = AsyncMock(return_value=mock_result)

        async def _mock_get_session():
            yield mock_session

        mock_manager = ConnectionManager()

        with (
            patch(
                "routers.ws_transcript._receive_auth_token",
                new_callable=AsyncMock,
                return_value="valid-token",
            ),
            patch(
                "routers.ws_transcript._validate_ws_token",
                return_value={"sub": "user_1", "org_id": "org_1"},
            ),
            patch(
                "routers.ws_transcript.get_session",
                _mock_get_session,
            ),
            patch("routers.ws_transcript.manager", mock_manager),
        ):
            with client.websocket_connect("/ws/calls/1/transcript") as ws:
                ws.receive_json()

            assert mock_manager.get_connection_count(1) == 0


class TestReceiveAuthToken:
    """[2.2-UNIT-413..414] Auth token receive helper"""

    @pytest.mark.asyncio
    async def test_2_2_unit_413_given_valid_json_with_token_when_receive_then_returns_token(
        self,
    ):
        from routers.ws_transcript import _receive_auth_token

        mock_ws = AsyncMock()
        mock_ws.receive_text = AsyncMock(return_value=json.dumps({"token": "my-jwt"}))

        with patch(
            "routers.ws_transcript.asyncio.wait_for",
            return_value=json.dumps({"token": "my-jwt"}),
        ):
            result = await _receive_auth_token(mock_ws)
        assert result == "my-jwt"

    @pytest.mark.asyncio
    async def test_2_2_unit_414_given_receive_timeout_when_receive_then_returns_none(
        self,
    ):
        from routers.ws_transcript import _receive_auth_token
        import asyncio

        mock_ws = AsyncMock()
        mock_ws.receive_text = AsyncMock(side_effect=asyncio.TimeoutError())

        with patch(
            "routers.ws_transcript.asyncio.wait_for",
            side_effect=asyncio.TimeoutError(),
        ):
            result = await _receive_auth_token(mock_ws)
        assert result is None
