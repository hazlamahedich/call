import httpx
import jwt
from jwt import PyJWKClient
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from typing import Optional

from config.settings import settings

AUTH_ERROR_CODES = {
    "AUTH_INVALID_TOKEN": "AUTH_INVALID_TOKEN",
    "AUTH_TOKEN_EXPIRED": "AUTH_TOKEN_EXPIRED",
    "AUTH_UNAUTHORIZED": "AUTH_UNAUTHORIZED",
    "AUTH_FORBIDDEN": "AUTH_FORBIDDEN",
}


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, jwks_url: str):
        super().__init__(app)
        self.jwks_url = jwks_url
        self._jwk_client: Optional[PyJWKClient] = None

    @property
    def jwk_client(self) -> PyJWKClient:
        if self._jwk_client is None:
            self._jwk_client = PyJWKClient(self.jwks_url)
        return self._jwk_client

    async def dispatch(self, request: Request, call_next):
        if self._should_skip_auth(request.url.path):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "code": AUTH_ERROR_CODES["AUTH_INVALID_TOKEN"],
                    "message": "Missing Authorization header",
                },
            )

        if not auth_header.lower().startswith("bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "code": AUTH_ERROR_CODES["AUTH_INVALID_TOKEN"],
                    "message": "Invalid Authorization header format",
                },
            )

        token = auth_header[7:]

        try:
            payload = await self._verify_token(token)
            request.state.org_id = payload.get("org_id")
            request.state.user_id = payload.get("sub")
            org_id = payload.get("org_id")
            if org_id:
                orgs = payload.get("orgs")
                if isinstance(orgs, dict):
                    org_role = orgs.get(org_id, {}).get("role")
                    if org_role:
                        request.state.user_role = org_role
                if not hasattr(request.state, "user_role"):
                    org_role = payload.get("org_role")
                    if org_role:
                        request.state.user_role = org_role
        except jwt.ExpiredSignatureError:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "code": AUTH_ERROR_CODES["AUTH_TOKEN_EXPIRED"],
                    "message": "Token has expired",
                },
            )
        except jwt.InvalidTokenError as e:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "code": AUTH_ERROR_CODES["AUTH_INVALID_TOKEN"],
                    "message": f"Invalid token: {str(e)}",
                },
            )

        return await call_next(request)

    SKIP_AUTH_PATHS = frozenset(
        ["/health", "/docs", "/openapi.json", "/webhooks/clerk", "/webhooks/vapi"]
    )
    SKIP_AUTH_PREFIXES = ("/docs", "/openapi.json", "/webhooks/vapi")

    def _should_skip_auth(self, path: str) -> bool:
        if path in self.SKIP_AUTH_PATHS:
            return True
        return path.startswith(self.SKIP_AUTH_PREFIXES)

    async def _verify_token(self, token: str) -> dict:
        signing_key = self.jwk_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            key=signing_key.key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
        return payload
