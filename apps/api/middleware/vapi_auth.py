import hashlib
import hmac

from fastapi import HTTPException, Request, status

from config.settings import settings


async def verify_vapi_signature(request: Request) -> None:
    signature = request.headers.get("vapi-signature")
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "VAPI_SIGNATURE_MISSING",
                "message": "Missing vapi-signature header",
            },
        )

    if not settings.VAPI_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "VAPI_NOT_CONFIGURED",
                "message": "VAPI_WEBHOOK_SECRET not configured",
            },
        )

    body = await request.body()
    expected = hmac.new(
        settings.VAPI_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(signature, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "VAPI_SIGNATURE_INVALID",
                "message": "Invalid webhook signature",
            },
        )
