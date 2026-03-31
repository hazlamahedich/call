import logging
from typing import Optional

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings

logger = logging.getLogger(__name__)

_RETRY_ATTEMPTS = 3
_RETRY_BACKOFF_BASE = 1.0
_CONNECT_TIMEOUT = 5.0
_READ_TIMEOUT = 10.0


async def initiate_call(
    phone_number: str,
    assistant_id: str,
    metadata: Optional[dict] = None,
) -> dict:
    url = f"{settings.VAPI_BASE_URL}/call/phone"
    headers = {
        "Authorization": f"Bearer {settings.VAPI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "phoneNumber": phone_number,
        "assistantId": assistant_id,
    }
    if metadata:
        payload["metadata"] = metadata

    last_error = None
    for attempt in range(_RETRY_ATTEMPTS):
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(_CONNECT_TIMEOUT)
            ) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException as e:
            last_error = e
            logger.warning(
                f"Vapi API timeout (attempt {attempt + 1}/{_RETRY_ATTEMPTS}): {e}"
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code >= 500:
                last_error = e
                logger.warning(
                    f"Vapi API server error (attempt {attempt + 1}/{_RETRY_ATTEMPTS}): {e}"
                )
            else:
                logger.error(f"Vapi API client error: {e}")
                raise
        except httpx.HTTPError as e:
            last_error = e
            logger.warning(
                f"Vapi API HTTP error (attempt {attempt + 1}/{_RETRY_ATTEMPTS}): {e}"
            )

        if attempt < _RETRY_ATTEMPTS - 1:
            import asyncio

            await asyncio.sleep(_RETRY_BACKOFF_BASE * (2**attempt))

    raise RuntimeError(
        f"Vapi API call failed after {_RETRY_ATTEMPTS} attempts: {last_error}"
    )
