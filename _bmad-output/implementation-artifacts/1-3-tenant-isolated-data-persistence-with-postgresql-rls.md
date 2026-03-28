# Story 1.3: Tenant-Isolated Data Persistence with PostgreSQL RLS

Status: complete

## Story

As a Security Officer,
I want to enforce Row-Level Security (RLS) on all database tables,
so that data from one tenant is never accessible to another.

## Acceptance Criteria

1. **RLS Policy Enforcement**: Given a Neon PostgreSQL database with multiple tenants, when a query is executed from the FastAPI service, then `jwt.org_id` from the Clerk token is used to set the `app.current_org_id` session variable. [Source: epics.md#Story 1.3]

2. **Query Scoping**: Given RLS policies are active, when any SELECT/UPDATE/DELETE query runs, then PostgreSQL RLS policies deny access to any rows where `tenant_id != current_org_id`. [Source: epics.md#Story 1.3]

3. **Cross-Tenant Isolation Test**: Given Tenant A and Tenant B exist with data, when a query for Tenant A is executed, then zero results are returned for Tenant B's data. [Source: epics.md#Story 1.3]

4. **Migration Infrastructure**: Given the database needs RLS policies, when migrations are run, then all tenant-scoped tables include `org_id` column with index and RLS policy. [Source: architecture.md#Step 4]

5. **Session Context Injection**: Given an authenticated API request, when the database connection is acquired, then the `org_id` from JWT claims is automatically injected into PostgreSQL session state (`SET app.current_org_id = org_id`). [Source: project-context.md#Database & Security]

6. **Performance Guardrail**: Given multi-tenant queries, when RLS is active, then all queries use indices that include `org_id` to prevent performance degradation. [Source: project-context.md#Database & Security]

## Tasks / Subtasks

- [x] Design tenant-scoped data model (AC: 1, 4)
  - [x] Define base SQLModel with `org_id: str` column for all tenant-scoped entities
  - [x] Identify which tables require RLS (Agencies, Clients, Leads, Calls, Scripts, KnowledgeBases)
  - [x] Identify which tables are platform-level (Users, PlatformConfig) - exempt from RLS

- [x] Create PostgreSQL RLS migrations (AC: 2, 4)
  - [x] Initialize Alembic if not already: `alembic init apps/api/migrations`
  - [x] Create migration: `alembic revision -m "enable_rls_on_tenant_tables"`
  - [x] Migration file naming: Use timestamp prefix (e.g., `20260321_001_enable_rls.py`)
    > **NOTE**: Alembic auto-generates revision hash prefixes. Left as-is for production.
  > **SKIPPED**: Alembic auto-generates revision hash prefixes (e.g., `eb48e89c217f`). Timestamp naming is a non-blocking convention improvement.
  - [x] Create `org_id` index on all tenant-scoped tables
  - [x] Create RLS policies: `CREATE POLICY tenant_isolation ON {table} USING (org_id = current_setting('app.current_org_id')::text)`
  - [x] Create bypass policy for platform admins: `CREATE POLICY platform_admin_bypass ON {table} USING (current_setting('app.is_platform_admin', true)::boolean = true)`

- [x] Implement session context injection (AC: 1, 5)
  - [x] Create `apps/api/database/session.py` with `set_tenant_context()` function
  - [x] Create FastAPI dependency that sets `app.current_org_id` on connection acquisition
  - [x] Integrate with existing `get_current_org_id()` dependency from story 1-2
  - [x] Handle missing `org_id` gracefully (raise `TenantContextError`)
  - [x] Ensure context is set PER CONNECTION, not per pool (critical for connection pooling)

- [x] Create tenant-scoped SQLModel base class (AC: 1, 4)
  - [x] Create `apps/api/models/base.py` with `TenantModel` base class
  - [x] Include `org_id: str` column with index
  - [x] Include `created_at`, `updated_at` timestamps
  - [x] Add `soft_delete` flag for future use
  - [x] Implement auto-population hook for `org_id` from session context

- [x] Create TenantService base class (AC: 1, 4)
  - [x] Create `apps/api/services/base.py` with `TenantService` class
  - [x] Implement `create_tenant_record()` with auto-population from session context
  - [x] Handle `TenantContextError` when org_id is missing

- [x] Implement cross-tenant isolation tests (AC: 3)
  - [x] Create `apps/api/tests/fixtures/test_rls.py` with isolation verification tests (12 tests in 6 classes)
  - [x] Create `apps/api/tests/conftest.py` with all shared fixtures (`db_session`, `tenant_a_session`, `tenant_b_session`)
  - [x] Create test fixture helper to set up Tenant A and Tenant B with test data
  - [x] Test Tenant A cannot read Tenant B's data
  - [x] Test Tenant A cannot update Tenant B's data
  - [x] Test Tenant A cannot delete Tenant B's data
  - [x] Test cross-tenant query returns empty result set
  - [x] **SECURITY REGRESSION**: Test RLS re-enabled after setup — uses non-superuser `test_rls_user` role for verification (superusers bypass RLS even with FORCE ROW LEVEL SECURITY)
  - [x] Test soft delete isolation within tenant scope
  - [x] Test RLS cannot be bypassed without explicit admin flag
  - [x] Test missing org_id raises TenantContextError
  - [x] Test TenantService requires context to be set

- [x] Implement full-chain integration test (AC: 1, 5)
  - [x] Create `apps/api/tests/test_rls_full_chain.py` for end-to-end RLS validation (6 tests)
  - [x] Test flow: Mock Clerk JWT → Auth middleware extracts org_id → Dependency injection → RLS session set → Query isolated
  - [x] Verify 403 response when org_id missing from JWT
  - [x] Verify correct tenant data returned for valid JWT

- [x] Create performance index verification (AC: 6)
  - [x] Create `apps/api/tests/test_rls_performance.py` (7 tests)
  - [x] Add `EXPLAIN ANALYZE` test for RLS queries
  - [x] Verify index usage on `org_id` column (check for `Index Scan` in explain output)
  - [x] Add latency assertion: RLS query overhead < 10ms
  - [x] Verify `list_all` respects tenant scope
  - [x] Verify `get_by_id` respects tenant scope
  - [x] Verify pagination respects tenant scope

- [x] Create shared types for tenant models (AC: 1)
  - [x] Define `TenantScoped` interface in `packages/types/tenant.ts`
  - [x] Add `org_id` field to all tenant-scoped TypeScript interfaces
 - [x] Run `turbo run types:sync` after changes

- [x] Add error codes for tenant context failures (AC: 5)
  - [x] Add `TENANT_CONTEXT_MISSING` to `packages/constants/index.ts`
  - [x] Add `TENANT_ACCESS_DENIED` for cross-tenant violations
  - [x] Add `TENANT_INVALID_ORG_ID` for malformed org IDs

## Dev Notes

### Architecture Compliance

- **Database**: Neon PostgreSQL 17 with Row-Level Security (RLS). [Source: architecture.md#Step 4]
- **Tenancy**: PostgreSQL RLS policies enforce agency/client data boundaries at the infrastructure level. [Source: architecture.md#Step 4]
- **Multi-tenancy Pattern**: Strict RLS on all tables using `jwt.org_id` from Clerk. [Source: project-context.md#Database & Security]
- **Naming Convention**: Backend uses `snake_case`; use `AliasGenerator` for JSON conversion. [Source: architecture.md#Step 5]

### Neon PostgreSQL Configuration

Neon is a serverless PostgreSQL provider with specific configuration needs:

```bash
# apps/api/.env
DATABASE_URL=postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
# Neon uses pooled connections by default - use direct connection for migrations
DATABASE_URL_DIRECT=postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
```

**Neon-Specific Notes:**
- Connection strings include `-pooler` suffix for pooled connections (use for app, not migrations)
- Neon supports branching for isolated test environments: `neon branch create test-rls`
- Use `DATABASE_URL_DIRECT` (without pooler) for Alembic migrations
- Session variables (`SET app.current_org_id`) work correctly with pooled connections when set per-transaction

**Setting Up Test Branch (Optional but Recommended):**
```bash
# Create isolated test environment
neon branch create test-rls --parent main
# Run tests against test branch
DATABASE_URL=$(neon connection-string test-rls) pytest apps/api/tests/test_rls.py
# Cleanup after tests
neon branch delete test-rls
```

### RLS Implementation Pattern

```sql
-- Enable RLS on table
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;

-- Create tenant isolation policy
CREATE POLICY tenant_isolation ON leads
  USING (org_id = current_setting('app.current_org_id')::text);

-- Create index for performance
CREATE INDEX idx_leads_org_id ON leads(org_id);

-- Platform admin bypass (optional)
-- NOTE: The 'true' parameter in current_setting() allows graceful fallback if GUC is not set
-- This prevents errors when app.is_platform_admin is not configured
CREATE POLICY platform_admin_bypass ON leads
  USING (current_setting('app.is_platform_admin', true)::boolean = true);

-- IMPORTANT: To use platform admin bypass, the GUC variable must be pre-configured:
-- Option 1: Set at role level (persistent)
--   ALTER ROLE platform_admin SET app.is_platform_admin = 'true';
-- Option 2: Set per-session (runtime)
--   SET app.is_platform_admin = true;
-- Option 3: Set per-transaction in application code
--   await session.execute(text("SET app.is_platform_admin = true"))
```

### Session Context Injection Pattern

**CRITICAL: Session variables must be set PER CONNECTION, not per pool.**

```python
# apps/api/database/session.py
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

async def set_tenant_context(session: AsyncSession, org_id: str) -> None:
    """
    Set tenant context for RLS. Must be called at start of each transaction.
    
    IMPORTANT: This sets the session variable on the current connection/transaction,
    not on the entire connection pool. Each new transaction must set this.
    
    SECURITY: Uses parameterized query to prevent SQL injection.
    """
    await session.execute(text("SELECT set_config('app.current_org_id', :org_id, false)"), {"org_id": org_id})

# Dependency integration with existing auth from story 1-2
from fastapi import Depends
from apps.api.dependencies.org_context import get_current_org_id
from apps.api.database.base import get_session

async def get_tenant_scoped_session(
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_org_id)
) -> AsyncGenerator[AsyncSession, None]:
    """
    Provides a database session with tenant context pre-configured for RLS.
    Use this instead of get_session for any tenant-scoped operations.
    """
    await set_tenant_context(session, org_id)
    yield session
```

### TenantModel Base Class with Auto-Population

```python
# apps/api/models/base.py
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel
from sqlalchemy import event
from sqlalchemy.orm import object_session

class TenantModel(SQLModel):
    """
    Base class for all tenant-scoped models.
    
    CRITICAL: org_id is auto-populated from session context on insert.
    The session must have app.current_org_id set via set_tenant_context().
    """
    org_id: str = Field(default=None, index=True, description="Tenant organization ID")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    soft_delete: bool = Field(default=False)
    
    # Auto-population is handled at the service/repository layer
    # by reading app.current_org_id from the session context
```

**Service Layer Pattern for Auto-Population:**
```python
# apps/api/services/base.py
from sqlalchemy import text
from apps.api.models.base import TenantModel

class TenantService:
    async def create_tenant_record(self, model: TenantModel, session: AsyncSession) -> TenantModel:
        """
        Create a tenant-scoped record with org_id auto-populated from session context.
        """
        # Get org_id from session context
        result = await session.execute(text("SELECT current_setting('app.current_org_id', true)"))
        org_id = result.scalar()
        
        if not org_id:
            raise TenantContextError("TENANT_CONTEXT_MISSING", "No tenant context set")
        
        model.org_id = org_id
        session.add(model)
        await session.commit()
        await session.refresh(model)
        return model
```

### Test Fixture Setup

```python
# apps/api/tests/fixtures/tenant.py
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

TEST_ORG_A = "org_test_001"
TEST_ORG_B = "org_test_002"

# NOTE: db_session fixture is defined in apps/api/tests/fixtures/database.py
# It provides an isolated AsyncSession with transaction rollback for test isolation

@pytest.fixture
async def tenant_a_session(db_session: AsyncSession) -> AsyncSession:
    """Session scoped to Tenant A"""
    # SECURITY: Use parameterized query to prevent SQL injection
    await db_session.execute(text("SELECT set_config('app.current_org_id', :org_id, false)"), {"org_id": TEST_ORG_A})
    yield db_session

@pytest.fixture
async def tenant_b_session(db_session: AsyncSession) -> AsyncSession:
    """Session scoped to Tenant B"""
    # SECURITY: Use parameterized query to prevent SQL injection
    await db_session.execute(text("SELECT set_config('app.current_org_id', :org_id, false)"), {"org_id": TEST_ORG_B})
    yield db_session

@pytest.fixture
async def setup_test_leads(db_session: AsyncSession) -> dict:
    """
    Create test leads for both tenants.
    IMPORTANT: Must disable RLS temporarily to insert cross-tenant test data.
    """
    # Disable RLS for setup
    await db_session.execute(text("SET app.is_platform_admin = true"))
    
    # Insert test data
    await db_session.execute(text("""
        INSERT INTO leads (org_id, name, email, phone, created_at, updated_at)
        VALUES 
            ('org_test_001', 'Lead A1', 'a1@test.com', '555-0001', NOW(), NOW()),
            ('org_test_001', 'Lead A2', 'a2@test.com', '555-0002', NOW(), NOW()),
            ('org_test_002', 'Lead B1', 'b1@test.com', '555-0003', NOW(), NOW())
    """))
    await db_session.commit()
    
    # Re-enable RLS
    await db_session.execute(text("SET app.is_platform_admin = false"))
    
    return {"tenant_a_count": 2, "tenant_b_count": 1}
```

**CRITICAL: db_session Fixture Source**
The `db_session` fixture must be defined in `apps/api/tests/fixtures/database.py`:
```python
# apps/api/tests/fixtures/database.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from apps.api.database.base import get_session

@pytest.fixture
async def db_session():
    """Provides an isolated database session with transaction rollback."""
    # Implementation depends on test database setup
    # See: apps/api/tests/conftest.py for full implementation
    async with async_sessionmaker(test_engine)() as session:
        async with session.begin():
            yield session
            await session.rollback()
```

### Tenant-Scoped Tables (Require RLS)

| Table | org_id Column | Notes |
|-------|---------------|-------|
| `agencies` | `org_id` | Maps to Clerk organization |
| `clients` | `org_id` | Sub-accounts under agency |
| `leads` | `org_id` | Lead/contact records |
| `calls` | `org_id` | Call session records |
| `scripts` | `org_id` | AI script configurations |
| `knowledge_bases` | `org_id` | RAG document chunks |
| `campaigns` | `org_id` | Outreach campaign configs |
| `usage_logs` | `org_id` | Call usage tracking |

### Platform-Level Tables (Exempt from RLS)

| Table | Notes |
|-------|-------|
| `users` | Cross-tenant user records (Clerk sync) |
| `platform_config` | Global platform settings |
| `subscriptions` | Platform billing (may need org_id for queries) |

### Previous Story Learnings (1-2)

- Clerk JWT validation middleware is implemented in `apps/api/middleware/auth.py`
- `get_current_org_id()` dependency exists in `apps/api/dependencies/org_context.py`
- Auth middleware extracts `org_id` from JWT and attaches to `request.state.org_id`
- Error codes pattern established in `packages/constants/index.ts`
- All tests use `unittest.mock` for external dependencies
- Playwright E2E tests require Clerk test fixtures

### Edge Case Handling

- **Missing org_id in JWT**: Return 403 with `TENANT_CONTEXT_MISSING` error code
- **Platform Admin Access**: Use `app.is_platform_admin` session variable for bypass
- **Connection Pooling**: Session variables must be set per-connection/transaction, not per-pool
- **Transaction Boundaries**: RLS context must be set within transaction scope (after BEGIN, before queries)

### Testing Requirements

- **Unit Tests**: RLS session injection tests in `apps/api/tests/test_rls.py`
- **Integration Tests**: Cross-tenant isolation verification
- **Performance Tests**: Index usage verification with `EXPLAIN ANALYZE`
- **Coverage Target**: >90% for RLS-related code (security-critical)

### Performance Benchmark Test Pattern

```python
# apps/api/tests/test_rls_performance.py
import pytest
from sqlalchemy import text
import time

@pytest.mark.asyncio
async def test_rls_query_performance(tenant_a_session):
    """
    AC6: Verify RLS queries use indices and maintain <10ms overhead.
    """
    # Execute query with EXPLAIN ANALYZE
    result = await tenant_a_session.execute(text("""
        EXPLAIN (ANALYZE, FORMAT JSON) 
        SELECT * FROM leads WHERE org_id = current_setting('app.current_org_id')
        LIMIT 100
    """))
    
    explain_output = result.scalar()
    plan = explain_output[0]
    
    # Verify index is used (not sequential scan)
    assert "Index Scan" in str(plan), f"Expected Index Scan, got: {plan}"
    
    # Verify execution time < 10ms
    execution_time_ms = plan.get("Execution Time", 0)
    assert execution_time_ms < 10, f"RLS query took {execution_time_ms}ms, expected <10ms"
```

### Project Structure Notes

```
apps/api/
├── database/
│   ├── base.py              # SQLModel base classes
│   ├── session.py           # Session management + tenant context injection
│   └── rls.py               # RLS helper functions (NEW)
├── models/
│   ├── base.py              # TenantModel base class (NEW)
│   ├── organization.py      # Agency/Client models (from 1-2)
│   ├── lead.py              # Lead model (NEW - for RLS testing)
│   └── ...
├── migrations/
│   ├── env.py               # Alembic environment config
│   └── versions/
│       └── 20260321_001_enable_rls.py  # Alembic migration for RLS
├── services/
│   └── base.py              # TenantService with auto-population (NEW)
└── tests/
    ├── fixtures/
    │   └── tenant.py        # Test fixtures for tenant sessions (NEW)
    ├── test_rls.py          # RLS isolation tests (NEW)
    ├── test_rls_performance.py  # Performance tests (NEW)
    └── test_session.py      # Session context tests (NEW)

packages/types/
├── tenant.ts                # Tenant-scoped interfaces (NEW)
└── ...

packages/constants/
└── index.ts                 # Add tenant error codes
```

### References

- [EPIC: epics.md#Epic 1: Multi-tenant Foundation & Identity]
- [Architecture: architecture.md#Step 4: Authentication & Security]
- [Architecture: architecture.md#Step 5: Implementation Patterns & Consistency Rules]
- [Project Context: project-context.md#Database & Security]
- [Previous Story: 1-2-multi-layer-hierarchy-clerk-auth-integration.md]
- [PostgreSQL RLS Docs: https://www.postgresql.org/docs/current/ddl-rowsecurity.html]
- [Neon Docs: https://neon.tech/docs/introduction]

## Dev Agent Record

### Agent Model Used
GLM-5

### Debug Log References
N/A

### Key Discoveries

1. **asyncpg `SET` limitation**: asyncpg does not support parameterized `SET` commands. Use `SELECT set_config('app.current_org_id', :org_id, false)` instead.
2. **SQLModel 0.0.34 inheritance bug**: When parent `SQLModel` has `Config.table = False`, child classes are NOT mapped as ORM entities. Workaround: use raw SQL via `text()`.
3. **async event loop conflicts**: Use `NullPool` and create a fresh engine per fixture to avoid connection reuse across loops.
4. **`CREATE POLICY IF NOT EXISTS` invalid**: Must `DROP POLICY IF EXISTS` first, then `CREATE POLICY`.
5. **Multiple SQL statements**: asyncpg does not support multiple statements in one `text()` call. Each statement must be separate.
6. **Table owner bypasses RLS**: Must add `ALTER TABLE leads FORCE ROW LEVEL SECURITY` so even table owner is subject to RLS.
7. **Superusers still bypass FORCE**: PostgreSQL superusers bypass RLS regardless of `FORCE ROW LEVEL SECURITY`. For test_009, created non-superuser `test_rls_user` role to verify real RLS enforcement.
8. **`TenantService.update()` duplicate column bug**: `__dict__` iteration includes `updated_at`/`created_at`, AND code appends `updated_at = NOW()`, causing PostgreSQL error. Fix: skip those fields in iteration.
9. **`TenantService.create()` needs explicit context check**: When session has `app.is_platform_admin=true`, RLS policies allow INSERT without `app.current_org_id`. Added `_ensure_tenant_context()`.
10. **`DROP ROLE` requires privilege revocation**: Must `REVOKE ALL ON SCHEMA/DATABASE/TABLE FROM role` before `DROP ROLE IF EXISTS`.

### Completion Notes

- All 6 acceptance criteria fully satisfied with **33/33 Story 1-3 tests passing**
- Implemented TenantModel base class with org_id, timestamps, soft_delete
- Fixed `set_tenant_context()` to use `set_config()` instead of `SET` (asyncpg limitation)
- Created centralized test fixtures in `tests/conftest.py` (schema setup, sessions, `test_rls_user` role)
- Created 12 RLS isolation tests in `tests/fixtures/test_rls.py` across 6 test classes
- Created 8 session context tests in `tests/test_session_context.py`
- Created 6 full-chain + middleware integration tests in `tests/test_rls_full_chain.py`
- Created 7 performance + query scoping tests in `tests/test_rls_performance.py`
- Fixed `TenantService.update()` duplicate column bug
- Added `_ensure_tenant_context()` guard to `TenantService.create()`
- Created `test_rls_user` non-superuser role for RLS verification (Discovery #7)
- Full test suite: **57 passed, 15 skipped, 0 failures**

### Test Quality Review

- **Review Date**: 2026-03-28
- **Score**: 82/100 (A - Good)
- **Recommendation**: Approve with Comments
- **Report**: [story-1-3-test-quality-review.md](../test-artifacts/story-1-3-test-quality-review.md)

**Key Findings**:

- 0 critical (P0) violations — no hard waits, no race conditions, no missing assertions
- 2 high (P1) issues: hardcoded DB URL fallback in test_009 (should use `pytest.skip()`), no data factory pattern
- 4 medium (P2) issues: conditional guard masking None bugs, fragile CI timing thresholds, global mutable schema flag, TRUNCATE CASCADE scope
- 2 low (P3) issues: test_rls.py slightly over 300 lines, magic strings in assertions

**Strengths Highlighted**:

- Excellent BDD docstrings with AC traceability across all 33 tests
- Non-superuser RLS verification demonstrates deep PostgreSQL security understanding
- Parameterized SQL in test fixtures prevents injection
- Per-connection engine isolation with NullPool eliminates context leakage

**Action Items**:

1. (P1) Replace hardcoded DB URL fallback with `pytest.skip()` in test_009
2. (P1) Create `LeadFactory` data factory for centralized test data generation
3. (P2) Assert `created.id is not None` instead of conditional guard in test_008
4. (P2) Add `CI_TIMEOUT_MULTIPLIER` env var for performance thresholds

### File List
- apps/api/database/session.py - Tenant context injection with TenantContextError
- apps/api/models/base.py - TenantModel base class
- apps/api/models/lead.py - Sample Lead model for testing
- apps/api/services/base.py - TenantService base class with raw SQL via text()
- apps/api/migrations/env.py - Alembic async environment
- apps/api/migrations/versions/eb48e89c217f_enable_rls_tenant_isolation.py - RLS migration
- apps/api/tests/__init__.py - Package init with sys.path
- apps/api/tests/conftest.py - Centralized test fixtures (schema, sessions, test_rls_user role)
- apps/api/tests/fixtures/conftest.py - sys.path setup only
- apps/api/tests/fixtures/test_rls.py - 12 RLS isolation tests (6 classes)
- apps/api/tests/test_session_context.py - 8 session context tests
- apps/api/tests/test_rls_full_chain.py - 6 full-chain + middleware tests
- apps/api/tests/test_rls_performance.py - 7 performance + query scoping tests
- packages/types/tenant.ts - TypeScript tenant interfaces
- packages/constants/index.ts - Added TENANT_ERROR_CODES
- _bmad-output/test-artifacts/story-1-3-test-quality-review.md - Test quality review report (82/100 A)

## Code Review Amendments (2026-03-28)

Post-implementation adversarial code review identified 27 findings across 3 review layers. All patch, intent gap, and deferred items have been resolved. Key spec clarifications:

### Finding #1 — `set_config` 3rd argument scope (Intent Gap)
**Clarification**: The 3rd argument to `set_config()` must be `true` (transaction-scoped), not `false` (session-scoped). Session-scoped variables persist across transactions and can leak tenant context in pooled connections. All code and tests updated.

### Finding #2 — `TenantService` was hardcoded to Lead columns (Intent Gap)
**Clarification**: `TenantService` must use generic column introspection (`model.model_fields`) rather than hardcoded Lead column lists. The `_row_to_instance()` method now dynamically discovers columns from any `TenantModel` subclass.

### Finding #4 — SQLModel `table=True` constructor silently drops base fields (Bad Spec)
**Root cause**: When constructing `Lead(org_id='x', soft_delete=True, ...)`, the SQLModel/Pydantic `__init__` silently ignores fields from the parent `TenantModel` class due to a known SQLModel bug with `table=True` models.
**Fix**: `_row_to_instance()` now uses `object.__setattr__()` for base fields after `__init__` with model-specific fields only.

### Finding #5 — Method name shadowed model field (Intent Gap)
**Clarification**: `soft_delete()` method shadowed the `soft_delete: bool` model field, causing attribute confusion. Methods renamed: `soft_delete()` → `mark_soft_deleted()`, `delete()` → `hard_delete()`.

### Additional fixes from deferred items:
- `datetime.utcnow` (deprecated) → `datetime.now(timezone.utc)` in `TenantModel`
- `_BASE_FIELDS` changed from `frozenset` to `set[str]` for type compatibility with `model_dump(exclude=)`
- `update()` now raises `TenantContextError` when RLS blocks cross-tenant updates (was silently returning)
- Test 004 updated to expect `TenantContextError` on cross-tenant update attempts
- Migration policies updated to include `platform_admin_bypass` on all 8 tenant tables

### TEA Automation — P1 Fixes Applied (2026-03-28)

Applied all P1 action items from test quality review (82/100) and expanded coverage for stories 1-1, 1-2, and 1-3.

**P1 Fixes Applied:**

1. **test_009 hardcoded DB URL fallback** — Replaced hardcoded `postgresql+asyncpg://test_rls_user@localhost:5432/call_test` fallback with `pytest.skip("TEST_RLS_DATABASE_URL not set")`. test_009 now correctly SKIPPED when env var not set.
2. **test_008 conditional guard** — Replaced `created.id if created.id else 0` with explicit `assert created.id is not None` before using the id. Fails fast on missing id.
3. **CI timeout multiplier** — Added `CI_MULTIPLIER = float(os.environ.get("CI_TIMEOUT_MULTIPLIER", "1.0"))` to `test_rls_performance.py`. Thresholds now scale on slower CI runners.

**New Tests Created:**

- `tests/test_constants.py` (rewritten from garbage) — Cross-source AUTH_ERROR_CODES sync (TS ↔ middleware ↔ dependencies), TENANT_ERROR_CODES verification. **4 tests**.
- `tests/test_error_codes_sync.py` — Backend error code consistency, key presence, format validation. **6 tests**.
- `tests/test_tenant_service.py` — TenantService edge cases: update with None id, create without context, _row_to_instance with full/truncated rows. **4 tests**.
- `tests/test_webhooks.py` — Added `membership.updated` and `membership.deleted` handler tests. **2 new tests**.
- `tests/test_auth.py` — Added auth skip path tests for `/health`, `/docs`, `/openapi.json` plus direct `_should_skip_auth()` unit tests. **6 new tests**.
- `tests/support/factories.py` — `LeadFactory` with `build()`, `build_batch()`, `reset()` for centralized test data generation.

**Test Results:** 78 passed, 16 skipped (contract tests), 0 failures — **94 total**

**Automation Summary:** `_bmad-output/test-artifacts/stories-1-1-1-2-1-3-automation-summary.md`

### File List (Updated)

- apps/api/database/session.py - Tenant context injection with TenantContextError
- apps/api/models/base.py - TenantModel base class
- apps/api/models/lead.py - Sample Lead model for testing
- apps/api/services/base.py - TenantService base class with raw SQL via text()
- apps/api/middleware/auth.py - AuthMiddleware with AUTH_ERROR_CODES and SKIP_AUTH_PATHS
- apps/api/dependencies/org_context.py - get_current_org_id with AUTH_ERROR_CODES
- apps/api/routers/webhooks.py - Clerk webhook handler with membership CRUD
- apps/api/migrations/env.py - Alembic async environment
- apps/api/migrations/versions/eb48e89c217f_enable_rls_tenant_isolation.py - RLS migration
- apps/api/tests/__init__.py - Package init with sys.path
- apps/api/tests/conftest.py - Centralized test fixtures (schema, sessions, test_rls_user role)
- apps/api/tests/fixtures/conftest.py - sys.path setup only
- apps/api/tests/fixtures/test_rls.py - 12 RLS isolation tests (P1 fixes applied: test_008, test_009)
- apps/api/tests/test_session_context.py - 8 session context tests
- apps/api/tests/test_rls_full_chain.py - 6 full-chain + middleware tests
- apps/api/tests/test_rls_performance.py - 7 performance + query scoping tests (CI multiplier added)
- apps/api/tests/test_constants.py - 4 cross-source error code sync tests (rewritten)
- apps/api/tests/test_error_codes_sync.py - 6 backend error code consistency tests (NEW)
- apps/api/tests/test_tenant_service.py - 4 TenantService edge case tests (NEW)
- apps/api/tests/test_auth.py - 12 auth middleware + skip path tests (6 new)
- apps/api/tests/test_webhooks.py - 10 webhook handler tests including membership.updated/deleted (2 new)
- apps/api/tests/support/__init__.py - Support package (NEW)
- apps/api/tests/support/factories.py - LeadFactory data factory (NEW)
- packages/types/tenant.ts - TypeScript tenant interfaces
- packages/constants/index.ts - Added TENANT_ERROR_CODES
- _bmad-output/test-artifacts/story-1-3-test-quality-review.md - Test quality review report (82/100 A)
- _bmad-output/test-artifacts/stories-1-1-1-2-1-3-automation-summary.md - TEA automation summary (NEW)
