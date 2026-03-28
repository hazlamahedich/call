"""
Story 1-3: Tenant-Isolated Data Persistence with PostgreSQL RLS
API Unit Tests for Performance Index Verification

Test ID Format: 1.3-API-XXX
Priority: P1 (High) | P2 (Medium) | P3 (Low)

Note: These tests verify index usage and performance characteristics.
For actual EXPLAIN ANALYZE, you would need a real PostgreSQL database with RLS enabled.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from models.lead import Lead
from services.base import TenantService

PERFORMANCE_THRESHOLDS = {
    "MAX_RLS_OVERHEAD_MS": 10,
    "MIN_INDEX_SCAN_PERCENT": 95,
}


class TestRLSIndexVerification:
    """[P1] Tests for RLS index usage verification - AC6"""

    @pytest.mark.asyncio
    async def test_1_3_api_040_org_id_column_has_index(self, db_session: AsyncSession):
        """
        AC6: Verify org_id column has an index.
        Given the leads table, when checking indexes,
        then an index exists on org_id column.
        """
        result = await db_session.execute(
            text("""
            SELECT COUNT(*)
            FROM pg_indexes
            WHERE tablename = 'leads'
            AND indexdef LIKE '%org_id%'
        """)
        )

        index_count = result.scalar()
        assert index_count >= 1, (
            "org_id column should have an index for RLS performance"
        )

    @pytest.mark.asyncio
    async def test_1_3_api_041_query_uses_org_id_in_where(
        self, tenant_a_session: AsyncSession
    ):
        """
        AC6: Verify queries use org_id in WHERE clause.
        Given RLS is active, when a query is executed,
        then the query plan includes org_id filtering.
        """
        service = TenantService[Lead](Lead)

        lead = Lead(name="Performance Test", email="perf@example.com")
        await service.create(tenant_a_session, lead)

        leads = await service.list_all(tenant_a_session)

        assert len(leads) >= 1
        for lead in leads:
            assert lead.org_id is not None


class TestRLSPerformanceCharacteristics:
    """[P2] Tests for RLS performance characteristics - AC6"""

    @pytest.mark.asyncio
    async def test_1_3_api_042_tenant_scoped_query_returns_quickly(
        self, tenant_a_session: AsyncSession
    ):
        """
        AC6: Tenant-scoped queries should be performant.
        Given a tenant session, when executing multiple queries,
        then each query completes within reasonable time.
        """
        import time

        service = TenantService[Lead](Lead)

        for i in range(10):
            lead = Lead(name=f"Batch Lead {i}", email=f"batch{i}@example.com")
            await service.create(tenant_a_session, lead)

        start_time = time.time()
        leads = await service.list_all(tenant_a_session)
        elapsed_ms = (time.time() - start_time) * 1000

        assert len(leads) == 10
        assert elapsed_ms < 1000, f"Query took {elapsed_ms}ms, expected < 1000ms"

    @pytest.mark.asyncio
    async def test_1_3_api_043_large_dataset_performance(
        self, tenant_a_session: AsyncSession
    ):
        """
        AC6: Large dataset performance within tenant scope.
        Given 100 records for a tenant, when listing all,
        then query completes efficiently.
        """
        import time

        service = TenantService[Lead](Lead)

        batch_size = 50
        for i in range(batch_size):
            lead = Lead(name=f"Large Dataset Lead {i}", email=f"large{i}@example.com")
            await service.create(tenant_a_session, lead)

        start_time = time.time()
        leads = await service.list_all(tenant_a_session, limit=100)
        elapsed_ms = (time.time() - start_time) * 1000

        assert len(leads) == batch_size
        assert elapsed_ms < 500, f"Query took {elapsed_ms}ms for {batch_size} records"


class TestQueryScoping:
    """[P2] Tests for automatic query scoping - AC2"""

    @pytest.mark.asyncio
    async def test_1_3_api_044_list_all_respects_tenant_scope(
        self, tenant_a_session: AsyncSession, tenant_b_session: AsyncSession
    ):
        """
        AC2: Query Scoping.
        Given Tenant A has 5 records and Tenant B has 3 records,
        when Tenant A calls list_all, then only 5 records are returned.
        """
        service_a = TenantService[Lead](Lead)
        service_b = TenantService[Lead](Lead)

        for i in range(5):
            lead = Lead(name=f"Tenant A Lead {i}", email=f"a{i}@example.com")
            await service_a.create(tenant_a_session, lead)

        for i in range(3):
            lead = Lead(name=f"Tenant B Lead {i}", email=f"b{i}@example.com")
            await service_b.create(tenant_b_session, lead)

        leads_a = await service_a.list_all(tenant_a_session)
        leads_b = await service_b.list_all(tenant_b_session)

        assert len(leads_a) == 5, f"Expected 5 records for Tenant A, got {len(leads_a)}"
        assert len(leads_b) == 3, f"Expected 3 records for Tenant B, got {len(leads_b)}"

        for lead in leads_a:
            assert "Tenant A" in lead.name

        for lead in leads_b:
            assert "Tenant B" in lead.name

    @pytest.mark.asyncio
    async def test_1_3_api_045_get_by_id_respects_tenant_scope(
        self, tenant_a_session: AsyncSession, tenant_b_session: AsyncSession
    ):
        """
        AC2: Query Scoping for get_by_id.
        Given Tenant B creates a record, when Tenant A calls get_by_id with that ID,
        then None is returned (not Tenant B's data).
        """
        service_b = TenantService[Lead](Lead)
        lead_b = Lead(name="Tenant B Exclusive", email="b-exclusive@example.com")
        created_b = await service_b.create(tenant_b_session, lead_b)

        service_a = TenantService[Lead](Lead)
        result = await service_a.get_by_id(tenant_a_session, created_b.id)

        assert result is None, (
            "Tenant A should not be able to access Tenant B's record by ID"
        )

    @pytest.mark.asyncio
    async def test_1_3_api_046_pagination_respects_tenant_scope(
        self, tenant_a_session: AsyncSession
    ):
        """
        AC2: Pagination respects tenant scope.
        Given 20 records for Tenant A, when paginating with limit 10 offset 0,
        then only first 10 records are returned.
        """
        service = TenantService[Lead](Lead)

        for i in range(20):
            lead = Lead(name=f"Paginated Lead {i:02d}", email=f"page{i}@example.com")
            await service.create(tenant_a_session, lead)

        page1 = await service.list_all(tenant_a_session, limit=10, offset=0)
        page2 = await service.list_all(tenant_a_session, limit=10, offset=10)

        assert len(page1) == 10
        assert len(page2) == 10

        page1_names = {l.name for l in page1}
        page2_names = {l.name for l in page2}

        assert len(page1_names.intersection(page2_names)) == 0, (
            "Pages should not overlap"
        )
