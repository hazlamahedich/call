"""
Story 1-3: Tenant-Isolated Data Persistence with PostgreSQL RLS
API Unit Tests for RLS-based Tenant Isolation

Test ID Format: 1.3-API-XXX
Priority: P0 (Critical) | P1 (High) | P2 (Medium) | P3 (Low)
"""

import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from models.lead import Lead
from services.base import TenantService
from database.session import set_tenant_context, TenantContextError
from tests.support.factories import LeadFactory

TEST_ORG_IDS = {
    "TENANT_A": "org_test_tenant_a",
    "TENANT_B": "org_test_tenant_b",
    "MISSING": None,
}


class TestTenantReadIsolation:
    """[P0] Tests for RLS-based read isolation - AC3"""

    @pytest.mark.asyncio
    async def test_1_3_api_001_tenant_a_cannot_see_tenant_b_data(
        self, tenant_a_session: AsyncSession, tenant_b_session: AsyncSession
    ):
        """
        AC3: Cross-tenant isolation test.
        Given Tenant A and Tenant B with data, when Tenant A queries,
        then zero results for Tenant B's data.
        """
        lead_service_a = TenantService[Lead](Lead)
        lead_service_b = TenantService[Lead](Lead)

        lead_b = LeadFactory.build(name="Tenant B Lead", email="tenant-b@example.com")
        await lead_service_b.create(tenant_b_session, lead_b)

        leads_for_a = await lead_service_a.list_all(tenant_a_session)

        assert len(leads_for_a) == 0, "Tenant A should not see Tenant B's data"

    @pytest.mark.asyncio
    async def test_1_3_api_002_cross_tenant_query_returns_empty(
        self, tenant_a_session: AsyncSession, tenant_b_session: AsyncSession
    ):
        """
        AC3: Cross-tenant query returns empty result set.
        Given Tenant B has data, when Tenant A queries with same ID,
        then empty result set is returned (not error).
        """
        lead_service_b = TenantService[Lead](Lead)

        lead_b = LeadFactory.build(name="Tenant B Lead", email="tenant-b@example.com")
        created_b = await lead_service_b.create(tenant_b_session, lead_b)

        lead_service_a = TenantService[Lead](Lead)
        result = await lead_service_a.get_by_id(tenant_a_session, created_b.id)

        assert result is None, (
            "Cross-tenant query should return None, not Tenant B's data"
        )

    @pytest.mark.asyncio
    async def test_1_3_api_003_tenant_can_retrieve_own_data(
        self, tenant_a_session: AsyncSession
    ):
        """
        Verify tenant can create and retrieve their own data.
        """
        lead_service = TenantService[Lead](Lead)

        lead = LeadFactory.build(name="Tenant A Lead", email="tenant-a@example.com")
        created_lead = await lead_service.create(tenant_a_session, lead)

        assert created_lead.id is not None
        assert created_lead.name == "Tenant A Lead"

        retrieved = await lead_service.get_by_id(tenant_a_session, created_lead.id)
        assert retrieved is not None
        assert retrieved.id == created_lead.id


class TestTenantUpdateIsolation:
    """[P0] Tests for RLS-based update isolation - AC3"""

    @pytest.mark.asyncio
    async def test_1_3_api_004_tenant_a_cannot_update_tenant_b_data(
        self, tenant_a_session: AsyncSession, tenant_b_session: AsyncSession
    ):
        """
        AC3: Tenant A cannot update Tenant B's data.
        Given Tenant B has a lead, when Tenant A attempts to update it,
        then update fails or data remains unchanged.
        """
        lead_service_b = TenantService[Lead](Lead)

        lead_b = LeadFactory.build(name="Tenant B Lead", email="tenant-b@example.com")
        created_b = await lead_service_b.create(tenant_b_session, lead_b)

        lead_service_a = TenantService[Lead](Lead)
        original_name = created_b.name

        created_b.name = "Hacked by Tenant A"
        with pytest.raises(TenantContextError) as exc_info:
            await lead_service_a.update(tenant_a_session, created_b)
        assert exc_info.value.error_code == "TENANT_ACCESS_DENIED"

        verify_service = TenantService[Lead](Lead)
        verified = await verify_service.get_by_id(tenant_b_session, created_b.id)

        assert verified is not None
        assert verified.name == original_name, (
            "Tenant B's data should not be modified by Tenant A"
        )

    @pytest.mark.asyncio
    async def test_1_3_api_005_tenant_can_update_own_data(
        self, tenant_a_session: AsyncSession
    ):
        """
        Verify tenant can update their own data.
        """
        lead_service = TenantService[Lead](Lead)

        lead = LeadFactory.build(name="Tenant A Lead", email="tenant-a@example.com")
        created = await lead_service.create(tenant_a_session, lead)

        created.name = "Updated Name"
        updated = await lead_service.update(tenant_a_session, created)

        assert updated is not None
        assert updated.name == "Updated Name"


class TestTenantDeleteIsolation:
    """[P0] Tests for RLS-based delete isolation - AC3"""

    @pytest.mark.asyncio
    async def test_1_3_api_006_tenant_a_cannot_delete_tenant_b_data(
        self, tenant_a_session: AsyncSession, tenant_b_session: AsyncSession
    ):
        """
        AC3: Tenant A cannot delete Tenant B's data.
        Given Tenant B has a lead, when Tenant A attempts to delete it,
        then delete fails or data remains.
        """
        lead_service_b = TenantService[Lead](Lead)

        lead_b = LeadFactory.build(name="Tenant B Lead", email="tenant-b@example.com")
        created_b = await lead_service_b.create(tenant_b_session, lead_b)

        lead_service_a = TenantService[Lead](Lead)
        delete_result = await lead_service_a.hard_delete(tenant_a_session, created_b.id)

        verify_service = TenantService[Lead](Lead)
        await tenant_b_session.execute(
            text("SELECT set_config('app.current_org_id', :org_id, true)"),
            {"org_id": TEST_ORG_IDS["TENANT_B"]},
        )
        verified = await verify_service.get_by_id(tenant_b_session, created_b.id)

        assert verified is not None, "Tenant B's data should not be deleted by Tenant A"
        assert verified.name == "Tenant B Lead"

    @pytest.mark.asyncio
    async def test_1_3_api_007_tenant_can_delete_own_data(
        self, tenant_a_session: AsyncSession
    ):
        """
        Verify tenant can delete their own data.
        """
        lead_service = TenantService[Lead](Lead)

        lead = LeadFactory.build(name="Tenant A Lead", email="tenant-a@example.com")
        created = await lead_service.create(tenant_a_session, lead)

        delete_result = await lead_service.hard_delete(tenant_a_session, created.id)

        assert delete_result is True

        retrieved = await lead_service.get_by_id(tenant_a_session, created.id)
        assert retrieved is None


class TestTenantSoftDelete:
    """[P1] Tests for soft delete isolation - AC3"""

    @pytest.mark.asyncio
    async def test_1_3_api_008_tenant_soft_delete_isolation(
        self, tenant_a_session: AsyncSession
    ):
        """
        Verify soft delete works within tenant scope.
        """
        lead_service = TenantService[Lead](Lead)

        lead = LeadFactory.build(name="To Delete", email="delete@example.com")
        created = await lead_service.create(tenant_a_session, lead)

        assert created.id is not None, "Created record must have an id"

        deleted = await lead_service.mark_soft_deleted(tenant_a_session, created.id)
        assert deleted is True

        retrieved = await lead_service.get_by_id(tenant_a_session, created.id)
        assert retrieved is None or retrieved.soft_delete is True


class TestSecurityRegression:
    """[P0] Security regression tests - AC3"""

    @pytest.mark.asyncio
    async def test_1_3_api_009_rls_re_enabled_after_setup(
        self, db_session: AsyncSession
    ):
        """
        SECURITY REGRESSION: Verify RLS is re-enabled after setup.
        Insert a row with admin session, then verify on a completely
        separate non-superuser connection that a different tenant cannot see it.
        """
        test_org = "org_test_regression"

        await db_session.execute(
            text("SELECT set_config('app.current_org_id', :org_id, true)"),
            {"org_id": test_org},
        )
        await db_session.execute(
            text("INSERT INTO leads (name, email) VALUES (:name, :email)"),
            {"name": "Regression Test Lead", "email": "regression@test.com"},
        )
        await db_session.commit()

        verify_url = os.environ.get("TEST_RLS_DATABASE_URL")
        if not verify_url:
            pytest.skip(
                "TEST_RLS_DATABASE_URL not set — skipping non-superuser RLS verification"
            )
        verify_engine = create_async_engine(verify_url, poolclass=NullPool)
        async with verify_engine.begin() as conn:
            await conn.execute(
                text("SELECT set_config('app.current_org_id', :org_id, true)"),
                {"org_id": "different_org"},
            )
            result = await conn.execute(text("SELECT COUNT(*) FROM leads"))
            count = result.scalar()
        await verify_engine.dispose()

        assert count == 0, "RLS should prevent cross-tenant access after re-enable"

    @pytest.mark.asyncio
    async def test_1_3_api_010_rls_cannot_be_bypassed_by_default(
        self, tenant_a_session: AsyncSession, tenant_b_session: AsyncSession
    ):
        """
        SECURITY REGRESSION: Verify RLS cannot be bypassed without explicit admin flag.
        Given Tenant B has data, when Tenant A queries without admin bypass,
        then RLS blocks access.
        """
        lead_service_b = TenantService[Lead](Lead)
        lead_b = LeadFactory.build(name="Tenant B Lead", email="tenant-b@example.com")
        await lead_service_b.create(tenant_b_session, lead_b)

        await tenant_a_session.execute(
            text("SELECT set_config('app.is_platform_admin', 'false', true)")
        )

        direct_query = await tenant_a_session.execute(
            text("SELECT COUNT(*) FROM leads WHERE org_id = :org_id"),
            {"org_id": TEST_ORG_IDS["TENANT_B"]},
        )
        direct_count = direct_query.scalar()

        assert direct_count == 0, (
            "Direct query should not see cross-tenant data when RLS active"
        )


class TestTenantContextError:
    """[P0] Tests for tenant context error handling - AC5"""

    @pytest.mark.asyncio
    async def test_1_3_api_011_missing_org_id_raises_error(
        self, db_session: AsyncSession
    ):
        """
        AC5: Missing org_id in context raises TenantContextError.
        Given no tenant context is set, when set_tenant_context is called with None,
        then TenantContextError is raised.
        """
        with pytest.raises(TenantContextError) as exc_info:
            await set_tenant_context(db_session, None)

        assert exc_info.value.error_code == "TENANT_CONTEXT_MISSING"

    @pytest.mark.asyncio
    async def test_1_3_api_012_tenant_service_requires_context(
        self, db_session: AsyncSession
    ):
        """
        AC5: TenantService requires tenant context to be set.
        Given no tenant context, when creating a record,
        then TenantContextError is raised.
        """
        lead_service = TenantService[Lead](Lead)
        lead = LeadFactory.build(name="Tenant A Lead", email="tenant-a@example.com")

        with pytest.raises(TenantContextError) as exc_info:
            await lead_service.create(db_session, lead)

        assert exc_info.value.error_code == "TENANT_CONTEXT_MISSING"
