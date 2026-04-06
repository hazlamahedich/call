"""Namespace guard middleware for tenant isolation.

Validates that authenticated org_id has access to requested resources.
Returns 403 for cross-tenant attempts with structured audit logging.
"""

import logging
import time
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_session as get_db
from dependencies.org_context import get_current_org_id
from config.settings import settings

logger = logging.getLogger(__name__)


async def verify_namespace_access(
    resource_id: int | None = None,
    request: Request | None = None,
    session: AsyncSession = Depends(get_db),
    org_id: str = Depends(get_current_org_id),
) -> str:
    """Verify that the authenticated org_id has access to the requested resource.

    Returns org_id if valid, raises 403 if namespace violation detected.
    Raises 404 if resource does not exist at all (no information leakage).
    """
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "NAMESPACE_VIOLATION",
                "message": "No organization context",
            },
        )

    if resource_id is not None and settings.NAMESPACE_GUARD_ENABLED:
        result = await session.execute(
            text(
                "SELECT org_id FROM knowledge_bases "
                "WHERE id = :resource_id AND soft_delete = false"
            ),
            {"resource_id": resource_id},
        )
        row = result.fetchone()

        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "KNOWLEDGE_BASE_NOT_FOUND",
                    "message": "Document not found",
                },
            )

        resource_owner_org_id = row[0]

        if resource_owner_org_id != org_id:
            logger.warning(
                "Namespace guard violation blocked",
                extra={
                    "code": "NAMESPACE_VIOLATION",
                    "org_id": org_id,
                    "attempted_resource_id": resource_id,
                    "resource_owner_org_id": resource_owner_org_id,
                    "endpoint": request.url.path if request else "unknown",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "NAMESPACE_VIOLATION",
                    "message": "Cross-tenant access denied",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

    return org_id
