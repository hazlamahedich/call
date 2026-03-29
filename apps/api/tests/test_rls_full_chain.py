"""
Story 1-3: Tenant-Isolated Data Persistence with PostgreSQL RLS
API Integration Tests for Full-Chain RLS Validation

Test ID Format: 1.3-API-XXX
Priority: P0 (Critical) | P1 (High) | P2 (Medium) | P3 (Low)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from models.lead import Lead
from services.base import TenantService
from database.session import set_tenant_context, TenantContextError
from tests.support.factories import LeadFactory

TEST_ORG_IDS = {
    "TENANT_A": "org_test_tenant_a",
    "TENANT_B": "org_test_tenant_b",
    "MISSING": None,
}

TEST_USER_IDS = {
    "USER_A": "user_test_a",
    "USER_B": "user_test_b",
}


def create_mock_jwt_payload(org_id: str, user_id: str) -> dict:
    """Create a mock JWT payload for testing."""
    return {
        "sub": user_id,
        "org_id": org_id,
        "email": f"test-{org_id}@example.com",
        "role": "admin",
    }


class TestFullChainRLS:
    """[P0] Integration tests for full-chain RLS validation - AC1, AC5"""

    @pytest.mark.asyncio
    async def test_1_3_api_030_valid_jwt_sets_tenant_context(
        self, tenant_a_session: AsyncSession
    ):
        """
        AC1: RLS Policy Enforcement.
        Given a valid tenant context, when a lead is created and listed,
        then app.current_org_id session variable is respected.
        """
        service = TenantService[Lead](Lead)
        lead = LeadFactory.build(name="Full Chain Test", email="chain@example.com")
        created = await service.create(tenant_a_session, lead)

        result = await tenant_a_session.execute(
            text("SELECT current_setting('app.current_org_id', true)")
        )
        current_org = result.scalar()

        assert current_org == TEST_ORG_IDS["TENANT_A"]
        assert created.org_id == TEST_ORG_IDS["TENANT_A"]

        leads = await service.list_all(tenant_a_session)
        assert len(leads) >= 1
        assert all(l.org_id == TEST_ORG_IDS["TENANT_A"] for l in leads)

    @pytest.mark.asyncio
    async def test_1_3_api_031_missing_org_id_returns_error(
        self, db_session: AsyncSession
    ):
        """
        AC5: Missing org_id raises TenantContextError.
        Given no tenant context, when creating a record,
        then TenantContextError with TENANT_CONTEXT_MISSING is raised.
        """
        service = TenantService[Lead](Lead)
        lead = LeadFactory.build(name="No Context", email="noctx@example.com")

        with pytest.raises(TenantContextError) as exc_info:
            await service.create(db_session, lead)

        assert exc_info.value.error_code == "TENANT_CONTEXT_MISSING"

    @pytest.mark.asyncio
    async def test_1_3_api_032_cross_tenant_data_isolation(
        self,
        db_session: AsyncSession,
        tenant_a_session: AsyncSession,
        tenant_b_session: AsyncSession,
    ):
        """
        AC3: Cross-tenant data isolation in full chain.
        Given Tenant A and Tenant B each have leads, when Tenant A queries,
        then only Tenant A's leads are returned.
        """
        service_a = TenantService[Lead](Lead)
        service_b = TenantService[Lead](Lead)

        lead_a = LeadFactory.build(name="Tenant A Lead", email="a@example.com")
        lead_b = LeadFactory.build(name="Tenant B Lead", email="b@example.com")

        await service_a.create(tenant_a_session, lead_a)
        await service_b.create(tenant_b_session, lead_b)

        leads_a = await service_a.list_all(tenant_a_session)
        leads_b = await service_b.list_all(tenant_b_session)

        assert len(leads_a) == 1
        assert leads_a[0].name == "Tenant A Lead"

        assert len(leads_b) == 1
        assert leads_b[0].name == "Tenant B Lead"

    @pytest.mark.asyncio
    async def test_1_3_api_033_org_id_auto_populated_on_create(
        self, tenant_a_session: AsyncSession
    ):
        """
        AC1: org_id auto-populated from session context.
        Given a session with tenant context, when a new record is created,
        then org_id is automatically set from app.current_org_id.
        """
        service = TenantService[Lead](Lead)

        lead = LeadFactory.build(name="Auto Populated", email="auto@example.com")
        created = await service.create(tenant_a_session, lead)

        assert created.org_id == TEST_ORG_IDS["TENANT_A"]


class TestMiddlewareIntegration:
    """[P0] Tests for middleware to session context integration - AC5"""

    @pytest.mark.asyncio
    async def test_1_3_api_034_middleware_extracts_org_id_to_request_state(self):
        """
        AC5: Auth middleware extracts org_id from JWT to request.state.
        Given a valid JWT with org_id claim, when middleware dispatch() processes the request,
        then org_id is attached to request.state.org_id.
        """
        from middleware.auth import AuthMiddleware

        middleware = AuthMiddleware(app=None, jwks_url="https://test.jwks.url")

        mock_payload = create_mock_jwt_payload(
            TEST_ORG_IDS["TENANT_A"], TEST_USER_IDS["USER_A"]
        )

        mock_request = MagicMock()
        mock_request.url.path = "/api/test"
        mock_request.headers = {"Authorization": "Bearer valid.token.here"}
        mock_request.state = MagicMock()

        mock_response = MagicMock()
        call_next = AsyncMock(return_value=mock_response)

        with patch.object(middleware, "_verify_token", return_value=mock_payload):
            await middleware.dispatch(mock_request, call_next)

        assert mock_request.state.org_id == TEST_ORG_IDS["TENANT_A"]
        assert mock_request.state.user_id == TEST_USER_IDS["USER_A"]
        call_next.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_1_3_api_035_missing_org_id_in_jwt_still_authenticates(self):
        """
        AC5: JWT without org_id still authenticates but request.state.org_id is None.
        Given a valid JWT without org_id claim, when middleware dispatch() processes the request,
        then authentication succeeds but request.state.org_id is None.
        """
        from middleware.auth import AuthMiddleware

        middleware = AuthMiddleware(app=None, jwks_url="https://test.jwks.url")

        mock_payload = {
            "sub": TEST_USER_IDS["USER_A"],
            "email": "test@example.com",
        }

        mock_request = MagicMock()
        mock_request.url.path = "/api/test"
        mock_request.headers = {"Authorization": "Bearer valid.token.here"}
        mock_request.state = MagicMock()

        mock_response = MagicMock()
        call_next = AsyncMock(return_value=mock_response)

        with patch.object(middleware, "_verify_token", return_value=mock_payload):
            await middleware.dispatch(mock_request, call_next)

        assert mock_request.state.org_id is None
        assert mock_request.state.user_id == TEST_USER_IDS["USER_A"]
        call_next.assert_called_once_with(mock_request)
