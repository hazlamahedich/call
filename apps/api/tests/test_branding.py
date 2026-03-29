"""
Story 1-5: White-labeled Admin Portal & Custom Branding
Backend Tests for Branding CRUD, RLS, Domain Verification, RBAC

Test ID Format: 1.5-API-XXX
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from models.agency_branding import AgencyBranding
from services.base import TenantService
from services.domain_verification import verify_cname, DomainVerificationResult
from database.session import TenantContextError

ORG_A = "org_branding_a"
ORG_B = "org_branding_b"

BRANDING_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS agency_branding (
    id SERIAL PRIMARY KEY,
    org_id VARCHAR NOT NULL,
    logo_url VARCHAR,
    primary_color VARCHAR(7) NOT NULL DEFAULT '#10B981',
    custom_domain VARCHAR(255),
    domain_verified BOOLEAN NOT NULL DEFAULT FALSE,
    brand_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    soft_delete BOOLEAN NOT NULL DEFAULT FALSE
);
"""

import os

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://sherwingorechomante@localhost:5432/call_test",
)

INDEX_SQL = (
    "CREATE INDEX IF NOT EXISTS ix_agency_branding_org_id ON agency_branding (org_id)"
)
POLICY_SQL = """
CREATE POLICY tenant_isolation_agency_branding ON agency_branding
    USING (org_id = current_setting('app.current_org_id', true)::text)
    WITH CHECK (org_id = current_setting('app.current_org_id', true)::text)
"""
POLICY_BYPASS_SQL = """
CREATE POLICY platform_admin_bypass_branding ON agency_branding
    USING (current_setting('app.is_platform_admin', true)::boolean = true)
    WITH CHECK (current_setting('app.is_platform_admin', true)::boolean = true)
"""


def _make_engine():
    return create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)


_schema_initialized = False


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _init_branding_schema():
    global _schema_initialized
    if _schema_initialized:
        yield
        return
    engine = _make_engine()
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS agency_branding CASCADE"))
        await conn.execute(text(BRANDING_SCHEMA_SQL))
        await conn.execute(text(INDEX_SQL))
        await conn.execute(
            text("ALTER TABLE agency_branding ENABLE ROW LEVEL SECURITY")
        )
        await conn.execute(text("ALTER TABLE agency_branding FORCE ROW LEVEL SECURITY"))
        await conn.execute(
            text(
                "DROP POLICY IF EXISTS tenant_isolation_agency_branding ON agency_branding"
            )
        )
        await conn.execute(
            text(
                "DROP POLICY IF EXISTS platform_admin_bypass_branding ON agency_branding"
            )
        )
        await conn.execute(text(POLICY_SQL))
        await conn.execute(text(POLICY_BYPASS_SQL))
        await conn.execute(
            text(
                "DROP TRIGGER IF EXISTS trg_agency_branding_set_org_id ON agency_branding"
            )
        )
        await conn.execute(
            text(
                "CREATE TRIGGER trg_agency_branding_set_org_id "
                "BEFORE INSERT ON agency_branding "
                "FOR EACH ROW EXECUTE FUNCTION set_org_id_from_context()"
            )
        )
    await engine.dispose()
    _schema_initialized = True
    yield


@pytest_asyncio.fixture(autouse=True)
async def _clean_branding_table():
    engine = _make_engine()
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE agency_branding CASCADE"))
    await engine.dispose()
    yield


@pytest_asyncio.fixture
async def admin_session():
    engine = _make_engine()
    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with factory() as session:
        await session.execute(
            text("SELECT set_config('app.is_platform_admin', 'true', true)")
        )
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def tenant_a_session():
    engine = _make_engine()
    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with factory() as session:
        await session.execute(
            text("SELECT set_config('app.current_org_id', :org_id, true)"),
            {"org_id": ORG_A},
        )
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def tenant_b_session():
    engine = _make_engine()
    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with factory() as session:
        await session.execute(
            text("SELECT set_config('app.current_org_id', :org_id, true)"),
            {"org_id": ORG_B},
        )
        yield session
    await engine.dispose()


@pytest.fixture
def branding_service():
    return TenantService[AgencyBranding](AgencyBranding)


class TestBrandingCRUD:
    """[1.5-API-001..010] Branding CRUD operations"""

    @pytest.mark.asyncio
    async def test_create_branding(self, tenant_a_session, branding_service):
        branding = AgencyBranding()
        branding.primary_color = "#FF0000"
        branding.brand_name = "Red Agency"
        result = await branding_service.create(tenant_a_session, branding)
        assert result.id is not None
        assert result.org_id == ORG_A
        assert result.primary_color == "#FF0000"
        assert result.brand_name == "Red Agency"

    @pytest.mark.asyncio
    async def test_read_branding(self, tenant_a_session, branding_service):
        branding = AgencyBranding()
        branding.primary_color = "#0000FF"
        branding.brand_name = "Blue Agency"
        created = await branding_service.create(tenant_a_session, branding)
        fetched = await branding_service.get_by_id(tenant_a_session, created.id)
        assert fetched is not None
        assert fetched.primary_color == "#0000FF"

    @pytest.mark.asyncio
    async def test_update_branding(self, tenant_a_session, branding_service):
        branding = AgencyBranding()
        created = await branding_service.create(tenant_a_session, branding)
        created.primary_color = "#ABCDEF"
        created.brand_name = "Updated"
        await branding_service.update(tenant_a_session, created)
        fetched = await branding_service.get_by_id(tenant_a_session, created.id)
        assert fetched is not None
        assert fetched.primary_color == "#ABCDEF"

    @pytest.mark.asyncio
    async def test_default_primary_color(self, tenant_a_session, branding_service):
        branding = AgencyBranding()
        created = await branding_service.create(tenant_a_session, branding)
        assert created.primary_color == "#10B981"

    @pytest.mark.asyncio
    async def test_branding_with_logo(self, tenant_a_session, branding_service):
        branding = AgencyBranding()
        branding.primary_color = "#10B981"
        branding.logo_url = "data:image/png;base64,iVBOR"
        created = await branding_service.create(tenant_a_session, branding)
        assert created.logo_url == "data:image/png;base64,iVBOR"

    @pytest.mark.asyncio
    async def test_branding_with_custom_domain(
        self, tenant_a_session, branding_service
    ):
        branding = AgencyBranding()
        branding.primary_color = "#10B981"
        branding.custom_domain = "custom.example.com"
        created = await branding_service.create(tenant_a_session, branding)
        assert created.custom_domain == "custom.example.com"
        assert created.domain_verified is False


class TestBrandingRLS:
    """[1.5-API-011..015] Tenant isolation for branding"""

    @pytest.mark.asyncio
    async def test_tenant_a_cannot_see_tenant_b(
        self, tenant_a_session, tenant_b_session, branding_service
    ):
        branding_b = AgencyBranding()
        branding_b.primary_color = "#0000FF"
        branding_b.brand_name = "B Brand"
        created_b = await branding_service.create(tenant_b_session, branding_b)
        fetched = await branding_service.get_by_id(tenant_a_session, created_b.id)
        assert fetched is None

    @pytest.mark.asyncio
    async def test_tenant_b_cannot_see_tenant_a(
        self, tenant_a_session, tenant_b_session, branding_service
    ):
        branding_a = AgencyBranding()
        branding_a.primary_color = "#FF0000"
        branding_a.brand_name = "A Brand"
        created_a = await branding_service.create(tenant_a_session, branding_a)
        fetched = await branding_service.get_by_id(tenant_b_session, created_a.id)
        assert fetched is None

    @pytest.mark.asyncio
    async def test_list_all_scoped_to_tenant(
        self, tenant_a_session, tenant_b_session, branding_service
    ):
        b1 = AgencyBranding()
        b1.primary_color = "#FF0000"
        await branding_service.create(tenant_a_session, b1)
        b2 = AgencyBranding()
        b2.primary_color = "#00FF00"
        await branding_service.create(tenant_a_session, b2)
        b3 = AgencyBranding()
        b3.primary_color = "#0000FF"
        await branding_service.create(tenant_b_session, b3)
        a_list = await branding_service.list_all(tenant_a_session)
        b_list = await branding_service.list_all(tenant_b_session)
        assert len(a_list) == 2
        assert len(b_list) == 1


class TestDomainVerification:
    """[1.5-API-016..020] DNS CNAME verification"""

    @pytest.mark.asyncio
    async def test_verify_cname_success(self):
        with patch(
            "services.domain_verification.dns.asyncresolver.Resolver"
        ) as mock_resolver_cls:
            mock_resolver = MagicMock()
            mock_resolver_cls.return_value = mock_resolver
            mock_rdata = MagicMock()
            mock_rdata.target = "cname.call.app."
            mock_resolver.resolve = AsyncMock(return_value=[mock_rdata])

            result = await verify_cname("custom.example.com", "cname.call.app")
            assert result.verified is True
            assert "verified" in result.message.lower()

    @pytest.mark.asyncio
    async def test_verify_cname_wrong_target(self):
        import dns.resolver

        with patch(
            "services.domain_verification.dns.asyncresolver.Resolver"
        ) as mock_resolver_cls:
            mock_resolver = MagicMock()
            mock_resolver_cls.return_value = mock_resolver
            mock_rdata = MagicMock()
            mock_rdata.target = "other.target.com."
            mock_resolver.resolve = AsyncMock(return_value=[mock_rdata])

            result = await verify_cname("custom.example.com", "cname.call.app")
            assert result.verified is False
            assert result.instructions is not None

    @pytest.mark.asyncio
    async def test_verify_cname_nxdomain(self):
        import dns.resolver

        with patch(
            "services.domain_verification.dns.asyncresolver.Resolver"
        ) as mock_resolver_cls:
            mock_resolver = MagicMock()
            mock_resolver_cls.return_value = mock_resolver
            mock_resolver.resolve.side_effect = dns.resolver.NXDOMAIN()

            result = await verify_cname("missing.example.com", "cname.call.app")
            assert result.verified is False
            assert "No CNAME" in result.message
            assert result.instructions is not None

    @pytest.mark.asyncio
    async def test_verify_cname_no_answer(self):
        import dns.resolver

        with patch(
            "services.domain_verification.dns.asyncresolver.Resolver"
        ) as mock_resolver_cls:
            mock_resolver = MagicMock()
            mock_resolver_cls.return_value = mock_resolver
            mock_resolver.resolve.side_effect = dns.resolver.NoAnswer()

            result = await verify_cname("noanswer.example.com", "cname.call.app")
            assert result.verified is False


class TestBrandingModelError:
    """[1.5-API-021..025] Model validation tests"""

    def test_agency_branding_model_fields(self):
        branding = AgencyBranding()
        assert branding.primary_color == "#10B981"
        assert branding.logo_url is None
        assert branding.custom_domain is None
        assert branding.domain_verified is False
        assert branding.brand_name is None
        branding.primary_color = "#ABCDEF"
        branding.logo_url = "data:image/png;base64,test"
        branding.custom_domain = "test.com"
        branding.domain_verified = True
        branding.brand_name = "Test Co"
        assert branding.primary_color == "#ABCDEF"
        assert branding.logo_url == "data:image/png;base64,test"
        assert branding.custom_domain == "test.com"
        assert branding.domain_verified is True
        assert branding.brand_name == "Test Co"

    def test_agency_branding_defaults(self):
        branding = AgencyBranding()
        assert branding.primary_color == "#10B981"
        assert branding.logo_url is None
        assert branding.custom_domain is None
        assert branding.domain_verified is False
        assert branding.brand_name is None

    def test_agency_branding_table_name(self):
        assert AgencyBranding.__tablename__ == "agency_branding"

    def test_agency_branding_extends_tenant_model(self):
        from models.base import TenantModel

        assert issubclass(AgencyBranding, TenantModel)
