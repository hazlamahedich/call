from typing import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import text

from config.settings import settings
from dependencies.org_context import get_current_org_id


class TenantContextError(Exception):
    """Raised when tenant context is missing or invalid."""

    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        self.message = message
        super().__init__(message)


async_engine = create_async_engine(
    settings.DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://"),
    echo=False,
)

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
            await session.rollback()
            raise


async def set_tenant_context(session: AsyncSession, org_id: str) -> None:
    """
    Set tenant context for RLS. Must be called at start of each transaction.

    IMPORTANT: This sets the session variable on the current connection/transaction,
    not on the entire connection pool. Each new transaction must set this.

    SECURITY: Uses parameterized query to prevent SQL injection.
    """
    if not org_id:
        raise TenantContextError(
            error_code="TENANT_CONTEXT_MISSING",
            message="No tenant context set",
        )
    await session.execute(
        text("SELECT set_config('app.current_org_id', :org_id, false)"),
        {"org_id": org_id},
    )


async def get_tenant_scoped_session(
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(lambda request: getattr(request.state, "org_id", None)),
) -> AsyncGenerator[AsyncSession, None]:
    """
    Provides a database session with tenant context pre-configured for RLS.
    Use this instead of get_session for any tenant-scoped operations.
    """
    if not org_id:
        raise TenantContextError(
            error_code="TENANT_CONTEXT_MISSING",
            message="No tenant context set",
        )
    await set_tenant_context(session, org_id)
    yield session
