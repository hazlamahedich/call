from fastapi import Request, HTTPException, status
from typing import Optional

AUTH_ERROR_CODES = {
    "AUTH_INVALID_TOKEN": "AUTH_INVALID_TOKEN",
    "AUTH_TOKEN_EXPIRED": "AUTH_TOKEN_EXPIRED",
    "AUTH_UNAUTHORIZED": "AUTH_UNAUTHORIZED",
    "AUTH_FORBIDDEN": "AUTH_FORBIDDEN",
}


async def get_current_org_id(request: Request) -> Optional[str]:
    org_id = getattr(request.state, "org_id", None)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": AUTH_ERROR_CODES["AUTH_FORBIDDEN"],
                "message": "Organization context required",
            },
        )
    return org_id


async def get_current_user_id(request: Request) -> Optional[str]:
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": AUTH_ERROR_CODES["AUTH_FORBIDDEN"],
                "message": "User authentication required",
            },
        )
    return user_id


async def get_optional_org_id(request: Request) -> Optional[str]:
    return getattr(request.state, "org_id", None)


async def get_optional_user_id(request: Request) -> Optional[str]:
    return getattr(request.state, "user_id", None)
