import asyncio
import json
import logging
from typing import Optional, Dict, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from jwt import PyJWKClient
import jwt as pyjwt

from config.settings import settings
from services.ws_manager import manager
from database.session import get_session

logger = logging.getLogger(__name__)

_shared_jwk_client: Optional[PyJWKClient] = None


def _get_shared_jwk_client() -> PyJWKClient:
    global _shared_jwk_client
    if _shared_jwk_client is None:
        _shared_jwk_client = PyJWKClient(settings.CLERK_JWKS_URL)
    return _shared_jwk_client


router = APIRouter(tags=["WebSocket Transcription"])


def _validate_ws_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        jwk_client = _get_shared_jwk_client()
        if jwk_client is None:
            return None
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        payload = pyjwt.decode(
            token,
            key=signing_key.key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
        return payload
    except Exception as e:
        logger.warning(
            "WebSocket auth failed",
            extra={"code": "WS_AUTH_FAILED", "error": str(e)},
        )
        return None


@router.websocket("/ws/calls/{call_id}/transcript")
async def transcript_websocket(
    websocket: WebSocket,
    call_id: int,
):
    token = await _receive_auth_token(websocket)
    if not token:
        await websocket.close(code=1008, reason="Auth token required")
        return

    payload = _validate_ws_token(token)
    if not payload:
        await websocket.close(code=1008, reason="Authentication failed")
        return

    org_id = payload.get("org_id")
    if not org_id:
        await websocket.close(code=1008, reason="Missing org_id in token")
        return

    async for session in get_session():
        call_result = await session.execute(
            text("SELECT org_id FROM calls WHERE id = :cid AND org_id = :oid"),
            {"cid": call_id, "oid": org_id},
        )
        if not call_result.first():
            await websocket.close(code=1008, reason="Call not found or access denied")
            return

    await manager.connect(websocket, call_id)
    try:
        await websocket.send_json({"type": "connected", "callId": call_id})
        while True:
            try:
                await websocket.receive_text()
            except Exception:
                break
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket, call_id)


async def _receive_auth_token(websocket: WebSocket) -> Optional[str]:
    try:
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=10)
        data = json.loads(raw)
        return data.get("token")
    except Exception as e:
        logger.debug(
            "WS auth token receive failed",
            extra={"code": "WS_AUTH_RECEIVE_FAILED", "error": str(e)},
        )
        return None
