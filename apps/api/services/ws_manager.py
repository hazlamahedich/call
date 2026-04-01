from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self._channels: Dict[int, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, call_id: int) -> None:
        await websocket.accept()
        async with self._lock:
            if call_id not in self._channels:
                self._channels[call_id] = set()
            self._channels[call_id].add(websocket)

    async def disconnect(self, websocket: WebSocket, call_id: int) -> None:
        async with self._lock:
            if call_id in self._channels:
                self._channels[call_id].discard(websocket)
                if not self._channels[call_id]:
                    del self._channels[call_id]

    async def broadcast_to_call(self, call_id: int, message: dict) -> None:
        connections = self._channels.get(call_id, set())
        if not connections:
            return

        disconnected = []
        for ws in list(connections):
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(
                    "WebSocket broadcast error",
                    extra={
                        "code": "WS_BROADCAST_ERROR",
                        "call_id": call_id,
                        "error": str(e),
                    },
                )
                disconnected.append(ws)

        for ws in disconnected:
            async with self._lock:
                if call_id in self._channels:
                    self._channels[call_id].discard(ws)

    def get_connection_count(self, call_id: int) -> int:
        return len(self._channels.get(call_id, set()))


manager = ConnectionManager()
