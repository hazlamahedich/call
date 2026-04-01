"""
Story 2.2: Real-time Audio Stream & Transcription Pipeline
WebSocket Tests - Auth, broadcast, and connection lifecycle

Test ID Format: [2.2-UNIT-XXX]
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.ws_manager import ConnectionManager


class TestConnectionManager:
    """[2.2-UNIT-400..406] ConnectionManager unit tests"""

    @pytest.mark.asyncio
    async def test_2_2_unit_400_P1_given_connect_when_called_then_tracks_websocket(
        self,
    ):
        manager = ConnectionManager()
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()

        await manager.connect(mock_ws, call_id=1)
        assert manager.get_connection_count(1) == 1

    @pytest.mark.asyncio
    async def test_2_2_unit_401_P1_given_multiple_connect_when_same_call_then_tracks_all(
        self,
    ):
        manager = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws1.accept = AsyncMock()
        ws2.accept = AsyncMock()

        await manager.connect(ws1, call_id=1)
        await manager.connect(ws2, call_id=1)
        assert manager.get_connection_count(1) == 2

    @pytest.mark.asyncio
    async def test_2_2_unit_402_P1_given_disconnect_when_called_then_removes_websocket(
        self,
    ):
        manager = ConnectionManager()
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()

        await manager.connect(mock_ws, call_id=1)
        await manager.disconnect(mock_ws, call_id=1)
        assert manager.get_connection_count(1) == 0

    @pytest.mark.asyncio
    async def test_2_2_unit_403_P2_given_disconnect_last_when_called_then_removes_channel(
        self,
    ):
        manager = ConnectionManager()
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()

        await manager.connect(mock_ws, call_id=1)
        await manager.disconnect(mock_ws, call_id=1)
        assert 1 not in manager._channels

    @pytest.mark.asyncio
    async def test_2_2_unit_404_P0_given_broadcast_when_subscribers_then_all_receive(
        self,
    ):
        manager = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws1.accept = AsyncMock()
        ws2.accept = AsyncMock()
        ws1.send_json = AsyncMock()
        ws2.send_json = AsyncMock()

        await manager.connect(ws1, call_id=1)
        await manager.connect(ws2, call_id=1)

        msg = {"type": "transcript", "entry": {"id": 1, "text": "hello"}}
        await manager.broadcast_to_call(1, msg)

        ws1.send_json.assert_called_once_with(msg)
        ws2.send_json.assert_called_once_with(msg)

    @pytest.mark.asyncio
    async def test_2_2_unit_405_P2_given_broadcast_when_no_subscribers_then_no_error(
        self,
    ):
        manager = ConnectionManager()
        msg = {"type": "transcript", "entry": {"id": 1}}

        await manager.broadcast_to_call(999, msg)

    @pytest.mark.asyncio
    async def test_2_2_unit_406_P1_given_broadcast_when_send_fails_then_removes_connection(
        self,
    ):
        manager = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws1.accept = AsyncMock()
        ws2.accept = AsyncMock()
        ws1.send_json = AsyncMock(side_effect=Exception("Connection lost"))
        ws2.send_json = AsyncMock()

        await manager.connect(ws1, call_id=1)
        await manager.connect(ws2, call_id=1)

        msg = {"type": "transcript", "entry": {"id": 1}}
        await manager.broadcast_to_call(1, msg)

        assert manager.get_connection_count(1) == 1
