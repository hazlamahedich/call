"""
Story 1.7: Resource Guardrails - Usage Monitoring & Hard Caps
Database Integration Tests

Test ID Format: [1.7-DB-XXX]

These tests require a running PostgreSQL instance with the call_test database.
They exercise the full SQL path including RLS, triggers, and constraint enforcement.
"""

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://sherwingorechomante@localhost:5432/call_test",
)

TEST_RLS_DATABASE_URL = os.environ.get(
    "TEST_RLS_DATABASE_URL",
    "postgresql+asyncpg://test_rls_user@localhost:5432/call_test",
)

ORG_A = "org_db_test_a"
ORG_B = "org_db_test_b"

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS usage_logs (
    id SERIAL PRIMARY KEY,
    org_id VARCHAR,
    resource_type VARCHAR(50) DEFAULT 'call',
    resource_id VARCHAR(255) DEFAULT '',
    action VARCHAR(50) DEFAULT 'call_initiated',
    metadata_json VARCHAR(2000) DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    soft_delete BOOLEAN DEFAULT FALSE
)
"""

_CREATE_INDEX_SQL = (
    "CREATE INDEX IF NOT EXISTS ix_usage_logs_org_id ON usage_logs (org_id)"
)

_TRIGGER_FN_SQL = """
CREATE OR REPLACE FUNCTION set_usage_org_id()
RETURNS TRIGGER AS $$
BEGIN
    NEW.org_id = current_setting('app.current_org_id', true);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql
"""

_DROP_TRIGGER_SQL = "DROP TRIGGER IF EXISTS trg_usage_logs_org_id ON usage_logs"

_CREATE_TRIGGER_SQL = """
CREATE TRIGGER trg_usage_logs_org_id
    BEFORE INSERT ON usage_logs
    FOR EACH ROW
    EXECUTE FUNCTION set_usage_org_id()
"""

_POLICY_SQL = """
CREATE POLICY usage_tenant_isolation ON usage_logs
    USING (org_id = current_setting('app.current_org_id', true)::text)
    WITH CHECK (org_id = current_setting('app.current_org_id', true)::text)
"""

_POLICY_BYPASS_SQL = """
CREATE POLICY usage_admin_bypass ON usage_logs
    USING (current_setting('app.is_platform_admin', true)::boolean = true)
    WITH CHECK (current_setting('app.is_platform_admin', true)::boolean = true)
"""

_SCHEMA_INITIALIZED = False


def _make_engine():
    return create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)


def _make_rls_engine():
    return create_async_engine(TEST_RLS_DATABASE_URL, echo=False, poolclass=NullPool)


# Schema creation is expensive (~500ms), so we skip re-creation within the same process. Restart the test process after schema changes.
async def _ensure_schema():
    global _SCHEMA_INITIALIZED
    if _SCHEMA_INITIALIZED:
        return
    engine = _make_engine()
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS usage_logs CASCADE"))
        await conn.execute(text(_CREATE_TABLE_SQL))
        await conn.execute(text(_CREATE_INDEX_SQL))
        await conn.execute(text("ALTER TABLE usage_logs ENABLE ROW LEVEL SECURITY"))
        await conn.execute(text("ALTER TABLE usage_logs FORCE ROW LEVEL SECURITY"))
        await conn.execute(
            text("DROP POLICY IF EXISTS usage_tenant_isolation ON usage_logs")
        )
        await conn.execute(
            text("DROP POLICY IF EXISTS usage_admin_bypass ON usage_logs")
        )
        await conn.execute(text(_POLICY_SQL))
        await conn.execute(text(_POLICY_BYPASS_SQL))
        await conn.execute(text(_TRIGGER_FN_SQL))
        await conn.execute(text(_DROP_TRIGGER_SQL))
        await conn.execute(text(_CREATE_TRIGGER_SQL))
        await conn.execute(text("REVOKE ALL ON usage_logs FROM test_rls_user"))
        await conn.execute(text("REVOKE ALL ON usage_logs FROM test_rls_user"))
        await conn.execute(
            text("GRANT SELECT, INSERT, UPDATE, DELETE ON usage_logs TO test_rls_user")
        )
        await conn.execute(
            text("GRANT USAGE, SELECT ON SEQUENCE usage_logs_id_seq TO test_rls_user")
        )
    await engine.dispose()
    _SCHEMA_INITIALIZED = True


@pytest_asyncio.fixture(autouse=True, scope="module")
async def _init_usage_schema():
    await _ensure_schema()
    yield


@pytest_asyncio.fixture(autouse=True)
async def _clean_usage_table():
    engine = _make_engine()
    async with engine.begin() as conn:
        try:
            await conn.execute(text("TRUNCATE usage_logs CASCADE"))
        except Exception:
            pass
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
    engine = _make_rls_engine()
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
    engine = _make_rls_engine()
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


async def _insert_usage_rows(
    session: AsyncSession, org_id: str, count: int, action: str = "call_initiated"
):
    await session.execute(
        text("SELECT set_config('app.current_org_id', :org_id, true)"),
        {"org_id": org_id},
    )
    for i in range(count):
        await session.execute(
            text(
                "INSERT INTO usage_logs (resource_type, resource_id, action, metadata_json) "
                "VALUES ('call', :rid, :action, '{}')"
            ),
            {"rid": f"{org_id}_call_{i:04d}", "action": action},
        )
    await session.flush()


class TestUsageLogsTenantIsolation:
    """[1.7-DB-001..003] RLS tenant isolation for usage_logs"""

    @pytest.mark.asyncio
    async def test_1_7_db_001_P0_given_two_orgs_with_rows_when_tenant_a_queries_then_sees_only_own_rows(
        self, admin_session, tenant_a_session
    ):
        await _insert_usage_rows(admin_session, ORG_A, 5)
        await _insert_usage_rows(admin_session, ORG_B, 5)
        await admin_session.commit()

        result = await tenant_a_session.execute(text("SELECT COUNT(*) FROM usage_logs"))
        count = result.scalar()
        assert count == 5

    @pytest.mark.asyncio
    async def test_1_7_db_002_P0_given_two_orgs_with_rows_when_tenant_b_queries_then_sees_only_own_rows(
        self, admin_session, tenant_b_session
    ):
        await _insert_usage_rows(admin_session, ORG_A, 3)
        await _insert_usage_rows(admin_session, ORG_B, 7)
        await admin_session.commit()

        result = await tenant_b_session.execute(text("SELECT COUNT(*) FROM usage_logs"))
        count = result.scalar()
        assert count == 7

    @pytest.mark.asyncio
    async def test_1_7_db_003_P0_given_tenant_inserts_with_wrong_org_id_when_row_persisted_then_trigger_overrides_org_id(
        self, tenant_a_session
    ):
        await tenant_a_session.execute(
            text(
                "INSERT INTO usage_logs (org_id, resource_type, resource_id, action) "
                "VALUES (:org_id, 'call', 'call_999', 'call_initiated')"
            ),
            {"org_id": ORG_B},
        )
        await tenant_a_session.flush()

        result = await tenant_a_session.execute(
            text("SELECT org_id FROM usage_logs WHERE resource_id = 'call_999'")
        )
        actual_org_id = result.scalar()
        assert actual_org_id == ORG_A
