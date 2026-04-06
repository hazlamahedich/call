import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio


def pytest_configure(config):
    config.addinivalue_line("markers", "p0: Critical path tests (smoke)")
    config.addinivalue_line("markers", "p1: High priority tests")
    config.addinivalue_line("markers", "p2: Medium priority tests")
    config.addinivalue_line(
        "markers", "integration: Integration tests requiring external resources"
    )


from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

sys.path.insert(0, str(Path(__file__).parent))

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://sherwingorechomante@localhost:5432/call_test",
)

TEST_RLS_DATABASE_URL = os.environ.get(
    "TEST_RLS_DATABASE_URL",
    "postgresql+asyncpg://test_rls_user@localhost:5432/call_test",
)

ORG_A = "org_test_tenant_a"
ORG_B = "org_test_tenant_b"

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS leads (
    id SERIAL PRIMARY KEY,
    org_id VARCHAR,
    name VARCHAR NOT NULL,
    email VARCHAR NOT NULL,
    phone VARCHAR,
    status VARCHAR DEFAULT 'new',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    soft_delete BOOLEAN DEFAULT FALSE
);
"""

_TRIGGER_FN_SQL = """
CREATE OR REPLACE FUNCTION set_org_id_from_context()
RETURNS TRIGGER AS $$
BEGIN
    NEW.org_id = current_setting('app.current_org_id', true);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

_DROP_TRIGGER_SQL = "DROP TRIGGER IF EXISTS trg_leads_set_org_id ON leads"

_CREATE_TRIGGER_SQL = """
CREATE TRIGGER trg_leads_set_org_id
    BEFORE INSERT ON leads
    FOR EACH ROW
    EXECUTE FUNCTION set_org_id_from_context();
"""

_POLICY_SQL = """
CREATE POLICY tenant_isolation ON leads
    USING (org_id = current_setting('app.current_org_id', true)::text)
    WITH CHECK (org_id = current_setting('app.current_org_id', true)::text);
"""

_POLICY_BYPASS_SQL = """
CREATE POLICY platform_admin_bypass ON leads
    USING (current_setting('app.is_platform_admin', true)::boolean = true)
    WITH CHECK (current_setting('app.is_platform_admin', true)::boolean = true)
"""

_INDEX_SQL = "CREATE INDEX IF NOT EXISTS ix_leads_org_id ON leads (org_id)"


async def _ensure_schema():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS leads CASCADE"))
        await conn.execute(text(_SCHEMA_SQL))
        await conn.execute(text(_INDEX_SQL))
        await conn.execute(text("ALTER TABLE leads ENABLE ROW LEVEL SECURITY"))
        await conn.execute(text("ALTER TABLE leads FORCE ROW LEVEL SECURITY"))
        await conn.execute(text("DROP POLICY IF EXISTS tenant_isolation ON leads"))
        await conn.execute(text("DROP POLICY IF EXISTS platform_admin_bypass ON leads"))
        await conn.execute(text(_POLICY_SQL))
        await conn.execute(text(_POLICY_BYPASS_SQL))
        await conn.execute(text(_TRIGGER_FN_SQL))
        await conn.execute(text(_DROP_TRIGGER_SQL))
        await conn.execute(text(_CREATE_TRIGGER_SQL))
        await conn.execute(text("REVOKE ALL ON SCHEMA public FROM test_rls_user"))
        await conn.execute(text("REVOKE ALL ON DATABASE call_test FROM test_rls_user"))
        await conn.execute(text("REVOKE ALL ON leads FROM test_rls_user"))
        await conn.execute(text("REVOKE ALL ON usage_logs FROM test_rls_user"))
        await conn.execute(
            text("REVOKE ALL ON SEQUENCE usage_logs_id_seq FROM test_rls_user")
        )
        await conn.execute(text("DROP ROLE IF EXISTS test_rls_user"))
        await conn.execute(text("CREATE ROLE test_rls_user WITH LOGIN"))
        await conn.execute(text("GRANT CONNECT ON DATABASE call_test TO test_rls_user"))
        await conn.execute(text("GRANT USAGE ON SCHEMA public TO test_rls_user"))
        await conn.execute(
            text("GRANT SELECT, INSERT, UPDATE, DELETE ON leads TO test_rls_user")
        )
        await conn.execute(
            text("GRANT USAGE, SELECT ON SEQUENCE leads_id_seq TO test_rls_user")
        )
        await conn.execute(
            text("GRANT SELECT, INSERT, UPDATE, DELETE ON usage_logs TO test_rls_user")
        )
        await conn.execute(
            text("GRANT USAGE, SELECT ON SEQUENCE usage_logs_id_seq TO test_rls_user")
        )
    await engine.dispose()


_SCHEMA_INITIALIZED = False


@pytest.fixture(scope="session")
async def _init_schema():
    global _SCHEMA_INITIALIZED
    if not _SCHEMA_INITIALIZED:
        await _ensure_schema()
        _SCHEMA_INITIALIZED = True
    yield


def _make_engine():
    return create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )


@pytest_asyncio.fixture(autouse=True)
async def _clean_table():
    engine = _make_engine()
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE leads CASCADE"))
    await engine.dispose()
    yield


@pytest_asyncio.fixture
async def db_session():
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
def mock_request_state():
    from unittest.mock import MagicMock

    mock_request = MagicMock()
    mock_request.state.org_id = "org_test_123"
    mock_request.state.user_id = "user_test_456"
    return mock_request
