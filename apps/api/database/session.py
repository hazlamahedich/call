from typing import AsyncGenerator, Optional

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import text
from sqlalchemy.pool import NullPool

from config.settings import settings
from dependencies.org_context import get_current_org_id


class TenantContextError(Exception):
    """Raised when tenant context is missing or invalid."""

    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        self.message = message
        super().__init__(message)


def _build_engine():
    url = settings.DATABASE_URL
    if "sqlite" in url:
        return create_async_engine(
            url.replace("sqlite://", "sqlite+aiosqlite://"),
            echo=False,
        )
    return create_async_engine(url, echo=False, poolclass=NullPool)


async_engine = _build_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Provides an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            try:
                await session.rollback()
            except Exception:
                pass
            raise


async def set_tenant_context(
    session: AsyncSession, org_id: Optional[str], *, is_local: bool = True
) -> None:
    if not org_id:
        raise TenantContextError(
            error_code="TENANT_CONTEXT_MISSING",
            message="No tenant context set",
        )
    await session.execute(
        text("SELECT set_config('app.current_org_id', :org_id, :is_local)"),
        {"org_id": org_id, "is_local": is_local},
    )


async def get_tenant_scoped_session(
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_org_id),
) -> AsyncGenerator[AsyncSession, None]:
    if not org_id:
        raise TenantContextError(
            error_code="TENANT_CONTEXT_MISSING",
            message="No tenant context set",
        )
    await set_tenant_context(session, org_id, is_local=True)
    try:
        yield session
    except Exception:
        try:
            await session.rollback()
        except Exception:
            pass
        raise
