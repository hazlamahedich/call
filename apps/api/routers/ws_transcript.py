import logging

import jwt as pyjwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from config.settings import settings
from services.ws_manager import manager

router = APIRouter(tags=["WebSocket Transcription"])
logger = logging.getLogger(__name__)


def _validate_ws_token(token: str) -> dict | None:
    try:
        from middleware.auth import AuthMiddleware

        auth_mw = AuthMiddleware(None, jwks_url=settings.CLERK_JWKS_URL)
        signing_key = auth_mw.jwk_client.get_signing_key_from_jwt(token)
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
    token: str = Query(...),
):
    payload = _validate_ws_token(token)
    if not payload:
        await websocket.close(code=1008, reason="Authentication failed")
        return

    org_id = payload.get("org_id")
    if not org_id:
        await websocket.close(code=1008, reason="Missing org_id in token")
        return

    await manager.connect(websocket, call_id)
    try:
        await websocket.send_json({"type": "connected", "callId": call_id})
        while True:
            try:
                data = await websocket.receive_text()
            except Exception:
                break
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket, call_id)
