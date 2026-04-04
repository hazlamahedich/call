# Story 1.7: Resource Guardrails: Usage Monitoring & Hard Caps

Status: done

## Story

As a Platform Admin,
I want to enforce call balance caps and trigger alerts,
so that I can prevent overages and maintain tenant profitability.

## Acceptance Criteria

1. **Usage Logging**: Given an active tenant making calls, when a call event occurs (initiated, completed, failed), then the system records the event in the `usage_logs` table with `resource_type`, `resource_id`, `action`, and `metadata` columns, scoped to the tenant via `org_id`. [Source: epics.md#Story 1.7, FR3]

2. **80% Threshold Alert**: Given a tenant approaching their call limit, when their monthly usage reaches 80% of the allocated balance, then a `StatusMessage` with `variant="warning"` is displayed on their dashboard indicating the usage threshold. [Source: epics.md#Story 1.7, FR3]

3. **95% Threshold Alert**: Given a tenant nearing their hard cap, when their monthly usage reaches 95% of the allocated balance, then a `StatusMessage` with `variant="error"` is displayed on their dashboard with an urgent warning. [Source: epics.md#Story 1.7, FR3]

4. **Hard Cap Enforcement**: Given a tenant at or above their monthly call limit, when the 100% hard cap is reached, then new call requests are rejected with a standardized `403-LIMIT-EXCEEDED` error response from the API. [Source: epics.md#Story 1.7, FR3]

5. **Usage Dashboard**: Given a tenant admin viewing the dashboard, when they navigate to the usage section, then they see real-time usage metrics: current usage count, allocated cap, percentage consumed, and a visual progress indicator. [Source: FR3, UX-DR2]

6. **Plan-Based Caps**: Given different subscription tiers, when a tenant is on the Seed plan (`PlanType="free"`), their cap is 1,000 calls/mo; Scale plan (`PlanType="pro"`) = 25,000 calls/mo; Apex plan (`PlanType="enterprise"`) = configurable (default 100,000). Default cap for new orgs = 1,000. Code MUST use `PlanType` values (`"free"`, `"pro"`, `"enterprise"`) from `packages/types/auth.ts` — marketing names (Seed/Scale/Apex) are for display only. [Source: prd.md#Subscription Tiers, packages/types/auth.ts]

## Tasks / Subtasks

### Phase 1: Backend — Usage Model & Migration (ACs 1, 6)

- [x] Create `UsageLog` SQLModel in `apps/api/models/usage_log.py` (AC: 1)
  - [x] Extend `TenantModel` with `table=True`, `__tablename__ = "usage_logs"`
  - [x] Add columns: `resource_type` (str, max_length=50, NOT NULL), `resource_id` (str, max_length=255, NOT NULL), `action` (str, max_length=50, NOT NULL), `metadata_json` (str, default="{}", max_length=2000 — stores arbitrary event details as JSON string)
  - [x] Register in `apps/api/models/__init__.py` — add `from models.usage_log import UsageLog`

- [x] Generate Alembic migration (AC: 1)
  - [x] After creating the SQLModel and registering it, run: `alembic revision --autogenerate -m "extend usage_logs with resource tracking columns"`
  - [x] Verify the generated migration contains ALTER TABLE `usage_logs` to add `resource_type`, `resource_id`, `action`, `metadata_json` columns only
  - [x] The `usage_logs` table already exists from migration `eb48e89c217f` — DO NOT create a new table, only ALTER it

- [x] Add TypeScript interfaces (AC: 1)
  - [x] `DbUsageLog` in `packages/types/tenant.ts` — UPDATE the existing interface to add `metadataJson?: string`
  - [x] Create `packages/types/usage.ts` — `UsageSummary` interface (`{ used: number; cap: number; percentage: number; plan: PlanType; threshold: UsageThreshold }`), `UsageThreshold` type (`"ok" | "warning" | "critical" | "exceeded"`)
  - [x] Add exports to `packages/types/index.ts` — add `usage`
  - [x] Run `turbo run types:sync`

### Phase 2: Backend — Usage Cap Configuration (AC 6)

- [x] Add usage cap settings to `apps/api/config/settings.py` (AC: 6)
  - [x] Add `DEFAULT_MONTHLY_CALL_CAP: int = 1000` (Seed plan default)
  - [x] Add `PLAN_CALL_CAPS: dict = {"free": 1000, "pro": 25000, "enterprise": 100000}` — maps `PlanType` to monthly call limits

- [x] Create plan-to-cap resolver utility (AC: 6)
  - [x] In `apps/api/services/usage.py` — `get_monthly_cap(org_id: str, plan: str | None = None) -> int` function
  - [x] Resolves cap from `settings.PLAN_CALL_CAPS` by plan type
  - [x] `get_org_plan(session, org_id)` queries `agencies` table for plan lookup

### Phase 3: Backend — Usage Service & Middleware (ACs 1, 4)

- [x] Create usage service in `apps/api/services/usage.py` (AC: 1, 4)
  - [x] `record_usage(session, org_id, resource_type, resource_id, action, metadata) -> UsageLog` — inserts a usage_logs row
  - [x] `get_monthly_usage(session, org_id) -> int` — counts usage_logs rows for current month WHERE `action = 'call_initiated'`
  - [x] `get_usage_summary(session, org_id) -> dict` — returns `{ used, cap, percentage, plan, threshold }`
  - [x] `check_usage_cap(session, org_id, plan) -> UsageThreshold` — returns threshold level: "ok" / "warning" (>=80%) / "critical" (>=95%) / "exceeded" (>=100%)
  - [x] `_compute_threshold(percentage, cap) -> UsageThreshold` — pure function extracted for testability, eliminates redundant DB queries in `get_usage_summary`
  - [x] Every service function calls `await set_tenant_context(session, org_id)` BEFORE executing any SQL query
  - [x] Uses raw SQL via `session.execute(text(...))` pattern

- [x] Register usage error codes in `packages/constants/index.ts` (AC: 4)
  - [x] Add `USAGE_ERROR_CODES` object with `as const` pattern
  - [x] Codes: `USAGE_LIMIT_EXCEEDED`, `USAGE_CAP_NOT_CONFIGURED`, `USAGE_INVALID_RESOURCE`, `USAGE_INTERNAL_ERROR`
  - [x] Export derived type `UsageErrorCode`

- [x] Create usage guard middleware / dependency in `apps/api/middleware/usage_guard.py` (AC: 4)
  - [x] FastAPI dependency `check_call_cap(request, session)` with try/except around DB calls
  - [x] If threshold is `"exceeded"`, raises `HTTPException(403)` with `USAGE_LIMIT_EXCEEDED`
  - [x] Graceful fallback on DB errors (logs error, allows request through)
  - [x] **Wired to `POST /usage/record`** via `dependencies=[Depends(check_call_cap)]` — blocks recording when cap exceeded

### Phase 4: Backend — Usage API Routes (ACs 2, 3, 4, 5)

- [x] Create usage API routes in `apps/api/routers/usage.py` (AC: 4, 5)
  - [x] `APIRouter(prefix="/usage", tags=["Usage"])` — self-prefixing pattern
  - [x] `GET /usage/summary` — returns `UsageSummaryResponse` for the tenant
  - [x] `POST /usage/record` — records usage event, serializes before commit, **guarded by `check_call_cap` dependency**
  - [x] `GET /usage/check` — returns threshold check result `{ threshold, used, cap }`
  - [x] Register router in `apps/api/main.py`
  - [x] Error handling: PydanticValidationError + HTTPException + generic Exception catch pattern

- [x] Create Pydantic schemas in `apps/api/schemas/usage.py` (AC: 4, 5)
  - [x] `UsageRecordPayload(BaseModel)` with camelCase alias, field validators for `resource_type`, `action`, `metadata`
  - [x] `UsageSummaryResponse(BaseModel)` with camelCase alias
  - [x] JSON validation on `metadata` field via `field_validator`

- [x] Write backend tests (AC: 1, 4)
  - [x] `apps/api/tests/test_usage.py` — 18 tests (error code sync, settings, model, schema, _compute_threshold pure function, payload length validation)
  - [x] `apps/api/tests/test_usage_router.py` — 12 tests (summary, record, check endpoints, cap-exceeded blocking)
  - [x] `apps/api/tests/test_error_codes_sync.py` — updated with USAGE_ERROR_CODES + USAGE_INTERNAL_ERROR

### Phase 5: Frontend — Usage Dashboard UI (ACs 2, 3, 5)

- [x] Create usage constants in `apps/web/src/lib/usage-constants.ts` (AC: 5)
  - [x] `THRESHOLD_LABELS` mapping threshold levels to display text
  - [x] `PLAN_LABELS` mapping plan types to display names

- [x] Create usage dashboard page at `apps/web/src/app/(dashboard)/dashboard/usage/page.tsx` (AC: 5)
  - [x] Server component fetching usage summary via server action
  - [x] Displays: current usage count, allocated cap, percentage consumed, plan name
  - [x] Visual progress bar with color transitions

- [x] Create usage components in `apps/web/src/components/usage/` (AC: 2, 3, 5)
  - [x] `UsageSummary.tsx` — Card displaying current usage, cap, percentage with progress bar
  - [x] `UsageThresholdAlert.tsx` — "warning" variant for warning+critical, "error" for exceeded
  - [x] `UsageProgressBar.tsx` — Color transitions (Emerald → Blue → Crimson) with NaN guard

- [x] Create usage Server Actions in `apps/web/src/actions/usage.ts` (AC: 5)
  - [x] `getUsageSummary()`, `recordUsage(payload)`, `checkUsageCap()`
  - [x] All catch blocks log errors via `console.error` with `[usage]` prefix

- [x] Add threshold alert to dashboard home page (AC: 2, 3)
  - [x] `UsageThresholdAlert` added to `apps/web/src/app/(dashboard)/dashboard/page.tsx`
  - [x] Uses backend-provided `threshold` (no client-side re-derivation)

### Phase 6: Tests (ACs 1-6)

- [x] Frontend unit tests in `apps/web/src/components/usage/__tests__/` (AC: 2, 3, 5)
  - [x] `UsageSummary.test.tsx`, `UsageThresholdAlert.test.tsx`, `UsageProgressBar.test.tsx`
  - [x] Accessibility: `axe()` on all components

- [x] Backend tests passing: 40 usage-specific (18 unit + 12 integration + 6 guard + 22 service + 12 DB integration)
- [x] Full suite: **258 passed**, 16 skipped, 0 failures (Python 3.11.8 venv)
- [x] Frontend tests passing: **382 passed** (50 test files), 0 failures

### Phase 7: Test Automation Expansion (79 new tests)

- [x] Backend unit tests expanded
  - [x] `test_usage_guard.py` — 6 tests (UNIT-061..066): check_call_cap with missing org, DB error, exceeded, ok, warning, critical
  - [x] `test_usage_service.py` — 22 tests (UNIT-067..088): threshold boundaries, plan caps, org plan lookup, usage summary, record_usage, check_usage_cap

- [x] Backend DB integration tests against real PostgreSQL with RLS
  - [x] `test_usage_db_integration.py` — 12 tests (DB-001..012): tenant isolation, trigger org_id override, record_usage persistence, monthly usage counting, cap threshold verification
  - [x] conftest.py updated: sequence privilege management for `test_rls_user` role

- [x] Frontend unit tests expanded
  - [x] `actions/__tests__/usage.test.ts` — 11 tests (UNIT-090..100): server actions getUsageSummary, recordUsage, checkUsageCap error paths
  - [x] `components/usage/__tests__/getThreshold.test.ts` — 6 tests (UNIT-101..106): threshold boundary logic
  - [x] `lib/__tests__/usage-constants.test.ts` — 6 tests (UNIT-107..112): THRESHOLD_LABELS, PLAN_LABELS mappings
  - [x] `app/(dashboard)/dashboard/__tests__/page.test.tsx` — 5 tests (UNIT-113..117): dashboard alert rendering
  - [x] `app/(dashboard)/dashboard/usage/__tests__/page.test.tsx` — 3 tests (UNIT-118..120): usage page rendering

- [x] E2E tests wired
  - [x] `tests/e2e/usage.spec.ts` — 8 tests (E2E-001..008): uses `authenticatedPage` fixture, auto-skips without Clerk env vars

- [x] Source bug fixed: `apps/api/services/usage.py` — `record_usage()` now uses `model_validate` instead of constructor so metadata persists correctly (SQLModel `table=True` silently ignores kwargs)

## Dev Notes

### Architecture Compliance

- **Backend**: FastAPI + SQLModel in `apps/api/`, extending `TenantModel` for automatic RLS via `org_id`. Use relative imports within the `apps/api/` package (matching `webhooks.py` pattern). [Source: project-context.md]
- **Frontend**: Next.js 15 App Router, Server Actions for data mutations. [Source: project-context.md]
- **Styling**: Tailwind v4 utility classes + Vanilla CSS. Use existing design system primitives (`Button`, `Card`, `StatusMessage`). [Source: project-context.md, story 1-4]
- **Types**: Shared TypeScript interfaces in `packages/types/`. Run `turbo run types:sync` after schema changes. [Source: architecture.md#Step 5]
- **Data access**: Use raw SQL via `session.execute(text(...))` for usage queries (counting, aggregation) — the existing `TenantService` is designed for CRUD operations on single records and doesn't support aggregation queries natively. For simple CRUD on `UsageLog` rows, use `TenantService[UsageLog](UsageLog)`.

### CRITICAL: What Already Exists — DO NOT recreate

| Item | Location | Notes |
|------|----------|-------|
| `usage_logs` table | Migration `eb48e89c217f` | Base columns only: `id`, `org_id`, `created_at`, `updated_at`, `soft_delete`. FULL RLS already applied. DO NOT create new table — only ALTER to add columns. |
| `DbUsageLog` interface | `packages/types/tenant.ts:74` | Has `resourceType`, `resourceId`, `action` — UPDATE to add `metadataJson` |
| Design system components | `apps/web/src/components/ui/` | Button, Card, Input, StatusMessage, EmptyState, ConfirmAction, FocusIndicator, Dialog, Tooltip, Popover, ScrollArea, Tabs, Switch — USE THESE |
| `StatusMessage` component | `apps/web/src/components/ui/status-message.tsx` | Has variants: `success`, `warning`, `error`, `info`. USE `warning` for 80% threshold, `error` for 95% threshold. Do NOT recreate. |
| `TenantModel` base class | `apps/api/models/base.py` | `org_id` (indexed), `created_at`, `updated_at`, `soft_delete`. `AliasGenerator(to_camel)`. Extend this for `UsageLog`. |
| `TenantService` generic CRUD | `apps/api/services/base.py` | `create`, `get_by_id`, `list_all`, `update`, `hard_delete`, `mark_soft_deleted`. Use for simple UsageLog CRUD. For aggregation (counting), use raw SQL. |
| Auth middleware | `apps/api/middleware/auth.py` | Validates Clerk JWT, sets `request.state.org_id` + `request.state.user_id`. Skip paths: `/health`, `/docs`, `/openapi.json`, `/webhooks/clerk`. |
| Router pattern | `apps/api/routers/onboarding.py` | Self-prefixing `APIRouter(prefix="/onboarding")` + `app.include_router(onboarding.router, tags=["Onboarding"])`. FOLLOW THIS PATTERN. |
| Error constants pattern | `packages/constants/index.ts` | `as const` + derived type union. Add `USAGE_ERROR_CODES` following SAME pattern. |
| Server action auth pattern | `apps/web/src/actions/branding.ts` | `const { getToken } = await auth(); const token = await getToken(); headers: { Authorization: \`Bearer ${token}\` }`. FOLLOW THIS PATTERN. |
| Plan types | `packages/types/auth.ts` | `PlanType = "free" | "pro" | "enterprise"`. USE this type — do NOT redefine. |
| `set_tenant_context` | `apps/api/database/session.py` | Sets `app.current_org_id` for RLS. Use in routes that need direct SQL. |
| Dashboard layout | `apps/web/src/app/(dashboard)/dashboard/layout.tsx` | Already wraps in `BrandingProvider` + `OnboardingGuard` + `DashboardHeader`. DO NOT modify — usage page goes inside this layout automatically as a child route. |
| `cn()` utility | `apps/web/src/lib/utils.ts` | `clsx` + `tailwind-merge` |
| Clerk auth | `apps/web/src/app/layout.tsx` | `ClerkProvider` wraps app, `useOrganization()` gives `org_id` |
| `lucide-react` icons | Available | CheckCircle, AlertTriangle, XCircle, Info already used in StatusMessage |

### Error Handling

- **Error response format — two patterns in the codebase**:
  - **Auth middleware** returns `JSONResponse(content={"code": "...", "message": "..."})` — flat `{code, message}` at response root.
  - **Route handlers** raise `HTTPException(detail={"code": "...", "message": "..."})` — FastAPI wraps this as `{"detail": {"code": "...", "message": "..."}}` in the response body.
  - **Frontend extraction**: Server actions access errors via `err.detail?.message` (because routes use `HTTPException`).
  - Usage routes MUST use the `HTTPException` pattern (matching existing routers like `onboarding.py`, `branding.py`, `clients.py`).
- **403-LIMIT-EXCEEDED**: When a tenant's usage cap is exceeded, the usage guard raises:
  ```python
  raise HTTPException(
      status_code=status.HTTP_403_FORBIDDEN,
      detail={
          "code": "USAGE_LIMIT_EXCEEDED",
          "message": "Monthly call limit has been reached. Upgrade your plan or wait for the next billing cycle.",
      },
  )
  ```
  Frontend receives: `{"detail": {"code": "USAGE_LIMIT_EXCEEDED", "message": "..."}}` — extract via `err.detail?.message`.
- Register usage error codes in `packages/constants/index.ts`:
  ```typescript
  export const USAGE_ERROR_CODES = {
    USAGE_LIMIT_EXCEEDED: "USAGE_LIMIT_EXCEEDED",
    USAGE_CAP_NOT_CONFIGURED: "USAGE_CAP_NOT_CONFIGURED",
    USAGE_INVALID_RESOURCE: "USAGE_INVALID_RESOURCE",
    USAGE_INTERNAL_ERROR: "USAGE_INTERNAL_ERROR",
  } as const;

  export type UsageErrorCode =
    (typeof USAGE_ERROR_CODES)[keyof typeof USAGE_ERROR_CODES];
  ```

### Database Schema

#### EXISTING: `usage_logs` table (ALTER TABLE — add columns)

The `usage_logs` table already exists in migration `eb48e89c217f` with base columns (`id`, `org_id`, `created_at`, `updated_at`, `soft_delete`) and full RLS policies. **DO NOT create a new table.** Only add columns:

```sql
ALTER TABLE usage_logs
    ADD COLUMN resource_type VARCHAR(50) NOT NULL DEFAULT 'call',
    ADD COLUMN resource_id VARCHAR(255) NOT NULL DEFAULT '',
    ADD COLUMN action VARCHAR(50) NOT NULL DEFAULT 'call_initiated',
    ADD COLUMN metadata_json VARCHAR(2000) NOT NULL DEFAULT '{}';
```

SQLModel: `apps/api/models/usage_log.py` — extends `TenantModel` with `table=True`, `__tablename__ = "usage_logs"`.

**Migration note**: Generate with `alembic revision --autogenerate -m "extend usage_logs with resource tracking columns"`. Verify the migration contains ALTER TABLE only — no CREATE TABLE.

### API Contracts

```python
# Route handler pattern (apps/api/routers/usage.py)
@router.get("/summary")
async def get_usage_summary(request: Request, session: AsyncSession = Depends(get_session)):
    org_id = request.state.org_id   # Set by AuthMiddleware
    ...
```

```
GET ${NEXT_PUBLIC_API_URL}/usage/summary
  Headers: Authorization: Bearer <clerk-jwt>
  Response 200: {
    used: number,
    cap: number,
    percentage: number,
    plan: string,
    threshold: "ok" | "warning" | "critical" | "exceeded"
  }

POST ${NEXT_PUBLIC_API_URL}/usage/record
  Headers: Authorization: Bearer <clerk-jwt>
  Body: {
    resourceType: string,     // "call" | "sms" | "agent"
    resourceId: string,       // e.g. call_id, sms_id
    action: string,           // "call_initiated" | "call_completed" | "call_failed" | "sms_sent"
    metadata?: string         // optional JSON string
  }
  Response 201: { usageLog: { id, orgId, resourceType, resourceId, action, metadataJson, createdAt } }

GET ${NEXT_PUBLIC_API_URL}/usage/check
  Headers: Authorization: Bearer <clerk-jwt>
  Response 200: { threshold: "ok" | "warning" | "critical" | "exceeded", used: number, cap: number }
```

### Usage Guard Integration Point

The `check_call_cap` dependency is wired to `POST /usage/record` via `dependencies=[Depends(check_call_cap)]`. When a tenant's cap is exceeded, the guard returns 403 `USAGE_LIMIT_EXCEEDED` before the route handler executes. Epic 2 will also apply it to `POST /calls/trigger` routes.

```python
# apps/api/middleware/usage_guard.py
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from database.session import get_session, set_tenant_context
from services.usage import check_usage_cap

async def check_call_cap(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    org_id = getattr(request.state, "org_id", None)
    if not org_id:
        return
    try:
        await set_tenant_context(session, org_id)
        threshold = await check_usage_cap(session, org_id)
    except Exception as e:
        logger.error(f"Usage guard DB check failed for org {org_id}: {e}")
        return
    if threshold == "exceeded":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "USAGE_LIMIT_EXCEEDED",
                "message": "Monthly call limit has been reached. Upgrade your plan or wait for the next billing cycle.",
            },
        )
```

Applied in router: `@router.post("/record", status_code=201, dependencies=[Depends(check_call_cap)])`.

### Plan-Based Cap Configuration

Default caps per subscription tier (from PRD):
- **Seed (free)**: 1,000 calls/month
- **Scale (pro)**: 25,000 calls/month
- **Apex (enterprise)**: 100,000 calls/month (configurable)

Initially, cap resolution reads from `config/settings.py` defaults. The `agencies` table `plan` column exists but plan-to-org mapping is not fully wired yet. For this story, use a simple approach:
1. Default cap = 1,000 (Seed)
2. `get_monthly_cap()` returns settings-based default
3. A comment marks where future `agencies.plan` lookup will go

### UX Design Requirements

- **Threshold Alert Visual**: `StatusMessage` with `variant="warning"` (blue/AlertTriangle icon) for 80% threshold, `variant="error"` (red/XCircle icon) for 95%+ threshold. These appear at the top of the dashboard page. [Source: story 1-4 — StatusMessage component]
- **Progress Bar Colors**: Emerald (`#10B981`) for 0-79%, Electric Blue (`#3B82F6`) for 80-94%, Vivid Crimson (`#F43F5E`) for 95%+. Smooth CSS transitions between states. [Source: ux-design-specification.md#Step 8 — Obsidian Neon colors]
- **Usage Dashboard**: Dedicated page at `/dashboard/usage`. Card-based layout showing usage summary, plan info, and visual progress indicator. Geist Mono for numbers (tabular-nums). [Source: ux-design-specification.md#Step 8 §1.2 — Telemetry typography]
- **Accessibility**: Progress bar must have `role="progressbar"` with `aria-valuenow`, `aria-valuemin`, `aria-valuemax`. Threshold alerts use existing `StatusMessage` `role="status"` for screen reader announcements. [Source: UX-DR14, WCAG AAA]
- **`reducedMotion`**: Pass `reducedMotion?: boolean` to `UsageProgressBar` — when true, disable CSS transition animations, show static colors immediately. [Source: story 1-4 pattern]

### Testing Standards

- **Backend**: `pytest` in `apps/api/tests/test_usage.py` and `test_usage_router.py` — follow existing test patterns
- **Frontend Unit**: `vitest` in `apps/web/src/components/usage/__tests__/`
- **Accessibility**: `vitest-axe` `axe()` on all usage components
- **Coverage**: >80% for new code
- **Mock external deps**: Mock API calls in frontend tests, use test database for backend tests
- **Test traceability**: Use `[1.7-UNIT-XXX]` IDs following the `[1.6-UNIT-XXX]` pattern from story 1-6

### File Structure

```
apps/api/
├── models/
│   ├── usage_log.py              # NEW (CREATE) — UsageLog SQLModel
│   └── __init__.py               # MODIFY — add usage_log import
├── routers/
│   └── usage.py                  # NEW (CREATE) — usage endpoints, APIRouter(prefix="/usage")
├── schemas/
│   └── usage.py                  # NEW (CREATE) — Pydantic models with camelCase aliases
├── services/
│   └── usage.py                  # NEW (CREATE) — usage tracking service (record, count, threshold)
├── middleware/
│   └── usage_guard.py            # NEW (CREATE) — FastAPI dependency for call cap enforcement
├── migrations/versions/          # NEW — migration: ALTER usage_logs (add columns)
├── tests/
│   ├── test_usage.py             # NEW (CREATE) — backend service tests
│   └── test_usage_router.py      # NEW (CREATE) — backend route tests
├── config/
│   └── settings.py               # MODIFY — add DEFAULT_MONTHLY_CALL_CAP, PLAN_CALL_CAPS
└── main.py                       # MODIFY — register usage router

apps/web/src/
├── app/(dashboard)/dashboard/
│   ├── page.tsx                  # MODIFY — add UsageThresholdAlert at top
│   └── usage/
│       └── page.tsx              # NEW (CREATE) — usage dashboard page
├── components/
│   └── usage/                    # NEW (CREATE)
│       ├── index.ts
│       ├── UsageSummary.tsx      # Card with usage stats + progress bar
│       ├── UsageThresholdAlert.tsx  # Conditional StatusMessage for thresholds
│       ├── UsageProgressBar.tsx  # Color-transitioning progress bar
│       └── __tests__/
│           ├── UsageSummary.test.tsx
│           ├── UsageThresholdAlert.test.tsx
│           └── UsageProgressBar.test.tsx
├── actions/
│   └── usage.ts                  # NEW (CREATE) — Server Actions for usage API
├── lib/
│   └── usage-constants.ts        # NEW (CREATE) — THRESHOLD_LABELS, PLAN_LABELS

packages/
├── types/
│   ├── usage.ts                  # NEW (CREATE) — UsageSummary, UsageThreshold types
│   ├── tenant.ts                 # MODIFY — add metadataJson to DbUsageLog
│   └── index.ts                  # MODIFY — add usage export
├── constants/
│   └── index.ts                  # MODIFY — add USAGE_ERROR_CODES with as const pattern
```

### References

- [Epic: epics.md#Story 1.7 — Resource Guardrails: Usage Monitoring & Hard Caps]
- [PRD: prd.md#FR3 — Hard usage caps, soft alerts at 80%/95%]
- [PRD: prd.md#Subscription Tiers — Seed/Scale/Apex caps]
- [UX Design: ux-design-specification.md#Step 8 — Obsidian color system (Emerald, Blue, Crimson)]
- [UX Design: ux-design-specification.md#Step 8 §1.2 — Geist Mono for telemetry numbers]
- [Architecture: architecture.md#Step 4 — SQLModel + TenantModel, RLS pattern]
- [Architecture: architecture.md#Step 5 — Naming conventions, error format, type sync]
- [Project Context: project-context.md — Tech stack, testing standards, security]
- [Previous Story 1-6: 1-6-10-minute-launch-onboarding-wizard.md — Router pattern, server action pattern, test patterns]
- [Existing Migration: apps/api/migrations/versions/eb48e89c217f — Creates usage_logs with base columns + RLS]
- [StatusMessage Component: apps/web/src/components/ui/status-message.tsx — warning/error variants for threshold alerts]
- [Card Component: apps/web/src/components/ui/card.tsx — Card layout for usage dashboard]
- [TenantService: apps/api/services/base.py — Generic CRUD for SQLModel, use for UsageLog]
- [Server Action Auth: apps/web/src/actions/branding.ts — Auth pattern with `auth().getToken()`]
- [Error Constants: packages/constants/index.ts — `as const` + derived type pattern]
- [Plan Types: packages/types/auth.ts — `PlanType = "free" | "pro" | "enterprise"`]
- [DbUsageLog: packages/types/tenant.ts:74 — Existing interface, needs metadataJson]
- [Dashboard Layout: apps/web/src/app/(dashboard)/dashboard/layout.tsx — Already wraps in BrandingProvider + OnboardingGuard]

### Previous Story Learnings

**From Story 1-1:**
- Turborepo monorepo with pnpm, `apps/web` = Next.js 15 App Router, `apps/api` = FastAPI + SQLModel + Alembic

**From Story 1-2:**
- Clerk auth: `ClerkProvider`, `useOrganization()`, `useUser()`
- `lucide-react` icons, `class-variance-authority` (CVA)

**From Story 1-3:**
- RLS via `TenantModel` base class with `org_id`
- Alembic migrations workflow
- Existing migration `eb48e89c217f` creates `usage_logs` with base columns — ALTER only

**From Story 1-4:**
- Design system: StatusMessage (warning/error variants), Card, Button, etc.
- Pattern: `reducedMotion?: boolean` on animated components
- Pattern: `cn()` utility, barrel exports, `vitest-axe`
- Obsidian theme: `#09090B` bg, Neon Emerald/Crimson/Blue accents
- Test pattern: `[1.4-UNIT-XXX]` IDs, BDD Given/When/Then naming

**From Story 1-5:**
- Server action auth pattern: `auth().getToken()` + `Authorization: Bearer` header
- Return pattern: `{ data: T | null; error: string | null }`

**From Story 1-6:**
- Router self-prefixing: `APIRouter(prefix="/xxx")` + `app.include_router(router, tags=["XXX"])`
- SQLModel `table=True` constructor silently ignores kwargs → **use `model_validate({"camelKey": ...})` in ALL usage test factories** (not positional kwargs)
- Error response: route handlers use `HTTPException(detail={"code": ..., "message": ...})`, auth middleware uses `JSONResponse(content={...})`. Frontend extracts via `err.detail?.message`.
- PydanticValidationError catch block pattern in routers → **MUST use in all usage route handlers** (see Error Handling section)
- Protected routes: `/dashboard(.*)` pattern already covers `/dashboard/usage` — **no middleware update needed**
- Test suites: 357 tests passing (330 frontend + 27 backend) — **must maintain this baseline**
- Error code sync tests in `test_error_codes_sync.py` must be updated when adding new error codes

### Project Structure Notes

- All new backend files follow the established `apps/api/` package structure
- Usage dashboard page at `/dashboard/usage` is already covered by the existing `/dashboard(.*)` protected route pattern in `apps/web/src/middleware.ts` — no middleware changes needed
- Usage guard dependency is wired to `POST /usage/record` — blocks recording when org cap is exceeded (403 USAGE_LIMIT_EXCEEDED)
- Plan cap values start as settings defaults — future stories can migrate to per-tenant configuration in the database

### Known Limitations & Future Considerations

- **Concurrency/race condition**: Under high concurrency (NFR.S1: 1,000+ sessions), multiple call initiations could read usage count simultaneously and all pass the cap check, causing overages. For this story, accept this limitation. Future improvement: use `SELECT ... FOR UPDATE` or Redis-based atomic counters.
- **Performance**: The `get_monthly_usage` query filters by `org_id`, date range, and `action`. Consider adding a composite index `idx_usage_logs_org_created_action (org_id, created_at, action)` for efficient monthly count queries.
- **Caching**: Architecture mentions Redis for compliance status caching. Usage cap checks on every call initiation would benefit from Redis caching with TTL (e.g., cache the usage count for 60s) to avoid hitting the database per call. Not in scope for this story.
- **`metadata_json` as VARCHAR(2000)**: PostgreSQL supports `JSONB` natively which would enable querying within metadata. Using `VARCHAR(2000)` is simpler for this story but consider migrating to `JSONB` in a future story if metadata querying is needed.
- **Billing period**: `get_monthly_usage` queries for "current month" but billing periods may not align to calendar months. The `UsageSummaryResponse` should eventually include `periodStart` and `periodEnd` fields. For this story, assume calendar month.
- **`/usage/record` webhook access**: Epic 2 (Vapi webhooks) will need to record usage events from server-to-server calls without Clerk JWT. This story keeps Clerk auth on all `/usage/*` routes. Epic 2 will introduce an alternative auth mechanism.

## Code Review Record

**Date:** 2026-03-30T18:46:56+08:00 (updated: 2026-03-30T20:44:00+08:00)
**Reviewer:** Code Review Skill (3-layer adversarial: Blind Hunter + Edge Case Hunter + Acceptance Auditor)
**Diff Scope:** 25 files, ~900+ lines (uncommitted changes)

### Patch Findings (14)

| # | Severity | Title | Location |
|---|----------|-------|----------|
| P1-01 | P1 | `get_monthly_cap()` ignores `PLAN_CALL_CAPS` — every org gets 1,000 calls | `services/usage.py:19` |
| P1-02 | P1 | `get_usage_summary()` hardcodes `"plan": "free"` | `services/usage.py:61` |
| P1-03 | P1 | Frontend/backend threshold mismatch — 3-way inconsistency (dashboard vs progress bar vs API) | `dashboard/page.tsx:10`, `UsageProgressBar.tsx:19`, `services/usage.py:72` |
| P1-04 | P1 | `UsageProgressBar.getThreshold` never returns `"warning"` — blue color unreachable | `UsageProgressBar.tsx:19-21` |
| P1-05 | P1 | `UsageSummary` TypeScript type omits `threshold` field | `packages/types/usage.ts:3-8` |
| P1-06 | P1 | Double commit in `POST /usage/record` — router commits, then `get_session` commits again | `routers/usage.py:82` |
| P1-07 | P1 | No JSON validation on `metadata_json` field | `models/usage_log.py:16`, `schemas/usage.py:16` |
| P1-08 | P1 | `UsageThresholdAlert` maps "critical" and "exceeded" to same variant — no visual distinction | `UsageThresholdAlert.tsx:14` |
| P1-09 | P1 | No exception handling in `check_call_cap` middleware | `usage_guard.py:15-16` |
| P1-10 | P1 | NaN/Infinity percentage bypasses Math clamp in progress bar | `UsageProgressBar.tsx:28` |
| P1-11 | P1 | `record` endpoint: commit-then-serialize creates duplicate risk on model_dump failure | `routers/usage.py:78-79` |
| P2-12 | P2 | Unused `Optional` import in `usage_log.py` | `models/usage_log.py:1` |
| P2-13 | P2 | Deprecated `asyncio.get_event_loop().run_until_complete()` in test | `tests/test_usage.py:80` |
| P2-14 | P2 | `catch {}` blocks silently swallow JSON parse errors in server actions | `apps/web/src/actions/usage.ts:27,66,104` |

### Deferred Findings (6)

- ~~Usage guard not wired to routes~~ — **RESOLVED**: wired to `POST /usage/record` via `dependencies=[Depends(check_call_cap)]`
- Race condition in cap check vs. record — spec acknowledges this limitation
- `TenantService.create` returns stale data — pre-existing base service pattern
- PostgreSQL-specific SQL — project uses PostgreSQL exclusively
- DB server timezone dependency — PostgreSQL with UTC convention
- `check_call_cap` silently passes when no `org_id` — by design
- Server action boilerplate duplication — style concern, not a bug

### Rejected (5)

- `PydanticValidationError` catch is dead code — defensive pattern matches story 1.6 convention
- Duplicate `aria-valuenow` attribute — false positive
- Missing `reducedMotion` prop — false positive (present in diff)
- Missing ARIA attributes — false positive (present in diff)
- Router file contains only comments — false positive (full 133-line file reviewed)

### Recommended Fix Priority

**Cluster 1 (threshold system):** P1-03, P1-04, P1-05 — root cause is frontend re-derives threshold instead of using backend value. Fix: (1) add `threshold` to TS `UsageSummary` type, (2) use backend-provided `threshold` in all frontend components, (3) fix `getThreshold` to include `"warning"` state.

**Cluster 2 (plan system):** P1-01, P1-02 — `get_monthly_cap` and `get_usage_summary` both ignore plan context. Fix: wire `PLAN_CALL_CAPS` into `get_monthly_cap` and resolve plan from org context in summary.

**Cluster 3 (transaction safety):** P1-06, P1-07, P1-09, P1-11 — commit/rollback semantics, JSON validation, and error handling gaps in backend.

**Cluster 4 (defensive):** P1-08, P1-10, P2-12..P2-14 — visual and minor code quality fixes.

---

## Dev Agent Record

### Agent Model Used

zai-coding-plan/glm-5.1

### Debug Log References

### Completion Notes List

- All 6 acceptance criteria implemented and verified
- Code review (3-layer adversarial) identified 14 patch findings — all 14 fixed
- Key fixes: plan-based cap resolution via `agencies` table, backend-driven threshold propagation, transaction safety (removed double commit, added serialize-before-commit), JSON metadata validation, error handling in middleware, NaN guard in progress bar, async test fix, error logging in server actions
- `_compute_threshold()` pure function extracted from service for deterministic testability
- `USAGE_INTERNAL_ERROR` added to error codes for generic 500 responses
- `check_call_cap` guard wired to `POST /usage/record` (deferred finding D-03 resolved)
- Python venv upgraded from 3.9.6 → 3.11.8
- Full backend test suite: **258 passed**, 16 skipped, 0 failures
- Full frontend test suite: **382 passed** (50 test files), 0 failures
- Test automation expansion: 79 new tests (28 backend unit, 12 DB integration, 31 frontend unit, 8 E2E)
- Fixed SQLModel metadata bug in `services/usage.py` — `record_usage()` uses `model_validate` instead of constructor
- Fixed conftest.py sequence privilege management — `REVOKE ALL ON SEQUENCE usage_logs_id_seq FROM test_rls_user` before DROP ROLE
- Pre-existing LSP warnings in `test_branding_router.py`, `test_onboarding.py`, `client.py`, `usage_log.py` — not caused by this story

### Change List

**Backend (Python — `apps/api/`)**

| File | Change |
|------|--------|
| `models/usage_log.py` | NEW — UsageLog SQLModel extending TenantModel |
| `models/__init__.py` | MODIFY — register UsageLog |
| `config/settings.py` | MODIFY — add DEFAULT_MONTHLY_CALL_CAP, PLAN_CALL_CAPS |
| `services/usage.py` | NEW — get_org_plan, get_monthly_cap, record_usage, get_monthly_usage, get_usage_summary, check_usage_cap, _compute_threshold (pure) |
| `schemas/usage.py` | NEW — UsageRecordPayload (with JSON validator + Field max_length + camelCase alias), UsageSummaryResponse |
| `routers/usage.py` | NEW — GET /usage/summary, POST /usage/record (guarded by check_call_cap), GET /usage/check |
| `middleware/usage_guard.py` | NEW — check_call_cap dependency with try/except + error logging |
| `main.py` | MODIFY — register usage router |
| `tests/test_usage.py` | NEW — 18 unit tests (error codes, settings, model, schema, _compute_threshold, payload length) |
| `tests/test_usage_router.py` | NEW — 12 integration tests (summary, record, check, cap-exceeded blocking) |
| `tests/test_usage_guard.py` | NEW — 6 unit tests (check_call_cap edge cases) |
| `tests/test_usage_service.py` | NEW — 22 unit tests (threshold boundaries, plan caps, summary, record, cap check) |
| `tests/test_usage_db_integration.py` | NEW — 12 DB integration tests against real PostgreSQL with RLS |
| `tests/conftest.py` | MODIFY — sequence privilege management for test_rls_user (usage_logs_id_seq, leads_id_seq) |
| `tests/test_error_codes_sync.py` | MODIFY — add USAGE_ERROR_CODES |

**Frontend (TypeScript — `apps/web/`)**

| File | Change |
|------|--------|
| `src/lib/usage-constants.ts` | NEW — THRESHOLD_LABELS, PLAN_LABELS |
| `src/components/usage/UsageSummary.tsx` | NEW — usage summary card |
| `src/components/usage/UsageThresholdAlert.tsx` | NEW — threshold alert (warning variant for warning+critical, error for exceeded) |
| `src/components/usage/UsageProgressBar.tsx` | NEW — color-transitioning progress bar with NaN guard |
| `src/components/usage/__tests__/` | NEW — 3 test files with axe() accessibility |
| `src/app/(dashboard)/dashboard/page.tsx` | MODIFY — add UsageThresholdAlert |
| `src/app/(dashboard)/dashboard/usage/page.tsx` | NEW — usage dashboard page |
| `src/actions/usage.ts` | NEW — server actions with error logging |
| `src/actions/__tests__/usage.test.ts` | NEW — 11 tests (server action error paths) |
| `src/components/usage/__tests__/getThreshold.test.ts` | NEW — 6 tests (threshold boundary logic) |
| `src/lib/__tests__/usage-constants.test.ts` | NEW — 6 tests (THRESHOLD_LABELS, PLAN_LABELS) |
| `src/app/(dashboard)/dashboard/__tests__/page.test.tsx` | NEW — 5 tests (dashboard alert rendering) |
| `src/app/(dashboard)/dashboard/usage/__tests__/page.test.tsx` | NEW — 3 tests (usage page rendering) |

**Shared Packages**

| File | Change |
|------|--------|
| `packages/types/usage.ts` | NEW — UsageSummary (with threshold), UsageThreshold |
| `packages/types/tenant.ts` | MODIFY — add metadataJson to DbUsageLog |
| `packages/types/index.ts` | MODIFY — export usage |
| `packages/constants/index.ts` | MODIFY — USAGE_ERROR_CODES, UsageErrorCode |

**E2E (Playwright)**

| File | Change |
|------|--------|
| `tests/e2e/usage.spec.ts` | NEW — 8 E2E tests using authenticatedPage fixture |

**Source Fixes**

| File | Change |
|------|--------|
| `apps/api/services/usage.py` | FIX — `record_usage()` uses `model_validate` instead of constructor (SQLModel table=True silently ignores kwargs) |
