"""Tenant isolation helper functions.

Shared utilities for enforcing tenant isolation across endpoints.
Reduces code duplication and ensures consistent security patterns.
"""

import logging
from typing import TypeVar, Type

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=object)


async def get_tenant_resource(
    session: AsyncSession,
    model: Type[T],
    resource_id: int,
    org_id: str,
    resource_name: str = "Resource",
) -> T | None:
    """Get a tenant-isolated resource by ID.

    This helper enforces tenant isolation by explicitly filtering by org_id,
    preventing potential RLS bypass through session.get().

    Args:
        session: Database session
        model: SQLAlchemy model class
        resource_id: ID of the resource to fetch
        org_id: Organization ID from JWT token
        resource_name: Human-readable resource name for error messages

    Returns:
        Model instance if found, None if not found

    Raises:
        HTTPException: Only logs warnings, doesn't raise for not found
    """
    result = await session.execute(
        select(model).where(
            model.id == resource_id,
            model.org_id == org_id,
        )
    )
    resource = result.scalar_one_or_none()

    if not resource:
        # Log potential tenant isolation violation attempt
        logger.warning(
            f"Tenant isolation violation attempt - {resource_name}",
            extra={
                "code": "TENANT_ISOLATION_VIOLATION",
                "org_id": org_id,
                f"attempted_{resource_name.lower()}_id": resource_id,
            },
        )

    return resource


async def require_tenant_resource(
    session: AsyncSession,
    model: Type[T],
    resource_id: int,
    org_id: str,
    resource_name: str = "Resource",
) -> T:
    """Get a tenant-isolated resource or raise 404.

    Like get_tenant_resource but raises HTTPException for not found cases.

    Args:
        session: Database session
        model: SQLAlchemy model class
        resource_id: ID of the resource to fetch
        org_id: Organization ID from JWT token
        resource_name: Human-readable resource name for error messages

    Returns:
        Model instance

    Raises:
        HTTPException: 404 if resource not found or access denied
    """
    resource = await get_tenant_resource(
        session=session,
        model=model,
        resource_id=resource_id,
        org_id=org_id,
        resource_name=resource_name,
    )

    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": f"{resource_name.upper().replace(' ', '_')}_NOT_FOUND",
                "message": f"{resource_name} not found or access denied",
            },
        )

    return resource
