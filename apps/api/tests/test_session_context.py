"""
Story 1-3: Tenant-Isolated Data Persistence with PostgreSQL RLS
API Unit Tests for Session Context Injection

Test ID Format: 1.3-API-XXX
Priority: P0 (Critical) | P1 (High) | P2 (Medium) | P3 (Low)
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import (
    set_tenant_context,
    get_tenant_scoped_session,
    get_session,
    TenantContextError,
)
from dependencies.org_context import get_current_org_id

TEST_ORG_IDS = {
    "VALID": "org_123",
    "ALT_VALID": "org_abc",
    "MISSING": None,
}


class TestSetTenantContext:
    """[P0] Tests for set_tenant_context function - AC5"""

    @pytest.mark.asyncio
    async def test_1_3_api_020_sets_org_id_in_session(self, db_session: AsyncSession):
        """
        AC5: Session context injection.
        Given a database session, when set_tenant_context is called with valid org_id,
        then app.current_org_id session variable is set.
        """
        org_id = TEST_ORG_IDS["VALID"]
        await set_tenant_context(db_session, org_id)

        result = await db_session.execute(
            text("SELECT current_setting('app.current_org_id', true)")
        )
        current_org_id = result.scalar()

        assert current_org_id == org_id

    @pytest.mark.asyncio
    async def test_1_3_api_021_prevents_sql_injection(self, db_session: AsyncSession):
        """
        SECURITY: Verify org_id is properly parameterized to prevent SQL injection.
        Given a malicious org_id with SQL characters, when set_tenant_context is called,
        then the injection is safely parameterized (no error).
        """
        malicious_org_id = "org_123'; DROP TABLE leads; --"
        await set_tenant_context(db_session, malicious_org_id)

        result = await db_session.execute(
            text("SELECT current_setting('app.current_org_id', true)")
        )
        current_org_id = result.scalar()

        assert current_org_id == malicious_org_id

    @pytest.mark.asyncio
    async def test_1_3_api_022_raises_error_for_none_org_id(
        self, db_session: AsyncSession
    ):
        """
        AC5: Missing org_id raises TenantContextError.
        Given None as org_id, when set_tenant_context is called,
        then TenantContextError is raised.
        """
        with pytest.raises(TenantContextError) as exc_info:
            await set_tenant_context(db_session, None)

        assert exc_info.value.error_code == "TENANT_CONTEXT_MISSING"
        assert "No tenant context set" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_1_3_api_023_raises_error_for_empty_org_id(
        self, db_session: AsyncSession
    ):
        """
        AC5: Empty string org_id raises TenantContextError.
        Given empty string as org_id, when set_tenant_context is called,
        then TenantContextError is raised.
        """
        with pytest.raises(TenantContextError) as exc_info:
            await set_tenant_context(db_session, "")

        assert exc_info.value.error_code == "TENANT_CONTEXT_MISSING"


class TestGetTenantScopedSession:
    """[P0] Tests for get_tenant_scoped_session dependency - AC5"""

    @pytest.mark.asyncio
    async def test_1_3_api_024_injects_org_id_into_session(self):
        """
        AC5: Session context injection via dependency.
        Given a mock request with org_id in state, when get_tenant_scoped_session is used,
        then session has app.current_org_id set.
        """
        mock_request = MagicMock()
        mock_request.state.org_id = TEST_ORG_IDS["VALID"]

        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.execute = AsyncMock()

        async def mock_get_session():
            yield mock_session

        async def mock_get_org_id(request):
            return request.state.org_id

        from unittest.mock import patch

        with patch("database.session.get_session", mock_get_session):
            with patch("database.session.get_current_org_id", mock_get_org_id):
                generator = get_tenant_scoped_session(
                    session=mock_session, org_id=TEST_ORG_IDS["VALID"]
                )
                session = await generator.__anext__()

                mock_session.execute.assert_called()
                call_args = mock_session.execute.call_args
                assert "app.current_org_id" in str(call_args[0][0])

    @pytest.mark.asyncio
    async def test_1_3_api_025_raises_error_for_missing_org_id(self):
        """
        AC5: Missing org_id raises TenantContextError in dependency.
        Given a mock request without org_id, when get_tenant_scoped_session is used,
        then TenantContextError is raised.
        """
        mock_request = MagicMock()
        mock_request.state.org_id = None

        mock_session = AsyncMock(spec=AsyncSession)

        with pytest.raises(TenantContextError) as exc_info:

            async def generator():
                async for session in get_tenant_scoped_session(
                    session=mock_session, org_id=None
                ):
                    yield session

            await generator().__anext__()

        assert exc_info.value.error_code == "TENANT_CONTEXT_MISSING"


class TestTenantContextPerConnection:
    """[P0] Tests for tenant context per-connection isolation - AC5"""

    @pytest.mark.asyncio
    async def test_1_3_api_026_context_isolated_per_connection(
        self, tenant_a_session: AsyncSession, tenant_b_session: AsyncSession
    ):
        """
        AC5: Session context must be per-connection, not per-pool.
        Given two tenant sessions with different contexts, when both are active,
        then each session has its own isolated context.
        """
        result_a = await tenant_a_session.execute(
            text("SELECT current_setting('app.current_org_id', true)")
        )
        org_id_a = result_a.scalar()

        result_b = await tenant_b_session.execute(
            text("SELECT current_setting('app.current_org_id', true)")
        )
        org_id_b = result_b.scalar()

        assert org_id_a != org_id_b
        assert "tenant_a" in org_id_a
        assert "tenant_b" in org_id_b

    @pytest.mark.asyncio
    async def test_1_3_api_027_context_persists_in_transaction(
        self, tenant_a_session: AsyncSession
    ):
        """
        AC5: Session context persists within transaction.
        Given a session with tenant context, when multiple queries are executed,
        then the context remains the same.
        """
        result1 = await tenant_a_session.execute(
            text("SELECT current_setting('app.current_org_id', true)")
        )
        org_id1 = result1.scalar()

        await tenant_a_session.execute(text("SELECT 1"))

        result2 = await tenant_a_session.execute(
            text("SELECT current_setting('app.current_org_id', true)")
        )
        org_id2 = result2.scalar()

        assert org_id1 == org_id2
