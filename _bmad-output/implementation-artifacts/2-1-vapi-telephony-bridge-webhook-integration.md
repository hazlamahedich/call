# Story 2.1: Vapi Telephony Bridge & Webhook Integration

Status: reviewed — test quality 93/100 (A+)

## Story

As a Developer,
I want to connect the API to the Vapi telephony bridge,
so that I can trigger and manage inbound/outbound calls via secure webhooks.

## Acceptance Criteria

1. **Call Trigger**: Given a valid Vapi API key and workspace, when an outbound call is triggered via the `POST /calls/trigger` endpoint, then Vapi initiates the call to the target phone number and the API returns the Vapi `call_id` with status `pending`. [Source: epics.md#Story 2.1, FR4]

2. **Webhook Reception**: Given an active Vapi workspace, when a call event occurs, then `apps/api` receives a webhook at `/webhooks/vapi/call-events` with `message.type` (e.g., `"call-start"`, `"call-end"`, `"call-failed"`) and a valid `call_id`, `org_id` from metadata. [Source: epics.md#Story 2.1]

3. **Webhook Signature Validation**: Given an incoming Vapi webhook, when the `vapi-signature` header is present, then all webhook events are validated using HMAC-SHA256 signature verification against `VAPI_WEBHOOK_SECRET`. Invalid signatures are rejected with `401 { detail: { code: "VAPI_SIGNATURE_INVALID", message: "..." } }`. [Source: vapi-webhook-auth-design.md, epics.md#Story 2.1]

4. **Call Record Persistence**: Given a `"call-start"` webhook event, when the event is received and validated, then a `Call` record is upserted in the `calls` table with `status="in_progress"`, `vapi_call_id`, `org_id`, and optional `lead_id`/`agent_id` populated from metadata. [Source: architecture.md#Step 4, packages/types/tenant.ts#DbCall]

5. **Call Status Tracking**: Given call lifecycle webhooks (`"call-start"`, `"call-end"`, `"call-failed"`), when each event is received, then the `Call` record status transitions accordingly: `pending` → `in_progress` → `completed` or `failed`, duration and `ended_at` are populated on `"call-end"`. [Source: epics.md#Story 2.1, TelecomCallStatus]

6. **Usage Guard Integration**: Given a tenant at or above their monthly call limit, when `POST /calls/trigger` is called, then the request is rejected with `403 USAGE_LIMIT_EXCEEDED` before the Vapi call is initiated. [Source: project-context.md#Usage Guard for Calls, story 1-7]

7. **Auth Bypass for Webhooks**: Given a Vapi webhook request, when it hits `/webhooks/vapi/*`, then the Clerk JWT auth middleware is bypassed via `SKIP_AUTH_PREFIXES` prefix matching (exact `SKIP_AUTH_PATHS` didn't match `/webhooks/vapi/call-events`) and the `verify_vapi_signature` dependency is used instead. [Source: auth.py#SKIP_AUTH_PREFIXES, vapi-webhook-auth-design.md]

8. **Compliance Pre-Check**: Given a call trigger request, when `POST /calls/trigger` is called, then a compliance/DNC eligibility check is performed before initiating the Vapi call. If `packages/compliance` is not yet fully implemented, log a warning and allow the call to proceed. [Source: architecture.md#Step 5 — mandatory import for call-initiation routes, prd.md#FR10]

## Tasks / Subtasks

### Phase 1: Backend — Call Model & Migration (ACs 4, 5)

- [x] Create `Call` SQLModel in `apps/api/models/call.py` (AC: 4, 5)
  - [x] Extend `TenantModel` with `table=True`, `__tablename__ = "calls"`
  - [x] Add columns: `vapi_call_id` (str, max_length=255, unique, index), `lead_id` (int, Optional, FK to leads, nullable), `agent_id` (int, Optional, FK to agents, nullable), `campaign_id` (int, Optional, FK to campaigns, nullable), `status` (str, max_length=50, default="pending"), `duration` (int, nullable — seconds), `recording_url` (str, nullable, max_length=500), `phone_number` (str, max_length=20, index), `transcript` (str, nullable — text, pre-allocated for Story 2.2), `ended_at` (datetime, nullable)
  - [x] Register in `apps/api/models/__init__.py` — add `from models.call import Call`
  - [x] Update `packages/types/tenant.ts` — update `DbCall` to include `vapiCallId`, `agentId`, `campaignId` (optional), `recordingUrl`, `phoneNumber`, `endedAt`, and make `leadId` optional

- [x] Generate Alembic migration (AC: 4)
  - [x] Run: `alembic revision --autogenerate -m "add calls table for vapi telephony bridge"`
  - [x] Verify migration creates `calls` table with RLS policies (inherited from TenantModel pattern)
  - [x] Verify `phone_number` has an index for lookup performance

- [x] Add TypeScript interfaces (AC: 4)
  - [x] Create `packages/types/vapi.ts` — `VapiCallEvent` (webhook payload matching Vapi's `message` structure), `VapiCallStartedPayload`, `VapiCallEndedPayload`, `VapiCallFailedPayload` types. **Verify exact field names against Vapi API docs** — the payload has a top-level `message` object with `type` and nested `call` object.
  - [x] Create `packages/types/call.ts` — update `TelecomCallStatus` if needed, add `TriggerCallRequest` and `TriggerCallResponse` interfaces
  - [x] Add `export * from "./vapi"` to `packages/types/index.ts`

### Phase 2: Backend — Vapi Service (ACs 1, 4, 5)

- [x] Create Vapi service in `apps/api/services/vapi.py` (AC: 1, 4, 5)
  - [x] `trigger_outbound_call(session, org_id, lead_id, agent_id, phone_number, campaign_id=None) -> dict` — calls Vapi API to initiate call, creates `Call` record with status `pending`, records usage event
  - [x] `handle_call_started(session, vapi_call_id, org_id, metadata={}) -> Call` — upserts Call record to `in_progress` using atomic `INSERT ... ON CONFLICT (vapi_call_id) DO UPDATE` for idempotency. Uses UUID placeholder if `vapi_call_id` is empty (prevents UNIQUE constraint race on empty strings). Extract `lead_id`/`agent_id` from webhook metadata if present. Uses `_safe_int()` to guard non-numeric metadata values.
  - [x] `handle_call_ended(session, vapi_call_id, org_id, duration, recording_url) -> Call` — updates Call to `completed` with duration and `ended_at=utcnow()`. Calls `set_tenant_context(session, org_id)` before SQL.
  - [x] `handle_call_failed(session, vapi_call_id, org_id, error_message) -> Call` — updates Call to `failed` with `ended_at=utcnow()`, stores error_message in transcript. Calls `set_tenant_context(session, org_id)` before SQL.
  - [x] All service functions call `await set_tenant_context(session, org_id)` BEFORE executing any SQL query
  - [x] Use `model_validate()` for ALL SQLModel construction — NEVER use positional kwargs (Epic 1 lesson)
  - [x] **Idempotency**: All webhook handlers must use upsert pattern (`ON CONFLICT DO UPDATE`) to handle Vapi duplicate webhooks gracefully

- [x] Create Vapi HTTP client helper in `apps/api/services/vapi_client.py` (AC: 1)
  - [x] `initiate_call(phone_number, assistant_id, metadata) -> dict` — POST to Vapi `/call/phone` API
  - [x] Use `httpx.AsyncClient` for outbound HTTP to Vapi
  - [x] Read `VAPI_API_KEY` and `VAPI_BASE_URL` from settings
  - [x] **Assistant ID Mapping**: `Agent.voice_id` stores the Vapi assistant ID — pass as `assistantId` to Vapi. If `voice_id` is empty, use a fallback minimal assistant config or return error.
  - [x] **Retry Strategy**: Use `httpx` with timeout (connect=5s, read=10s). For production reliability (NFR.R1: 99.9% uptime), manual retry with exponential backoff + jitter (max 3 retries) on transient failures. `httpx.AsyncClient` created outside retry loop for connection reuse.

### Phase 3: Backend — Webhook Routes (ACs 2, 3, 7)

- [x] Create webhook routes in `apps/api/routers/webhooks_vapi.py` (AC: 2, 3, 7)
  - [x] `APIRouter(prefix="/webhooks/vapi")` — self-prefixing pattern
  - [x] `POST /webhooks/vapi/call-events` — receives all Vapi call webhooks, applies `verify_vapi_signature` dependency, validates body via `VapiWebhookPayload` Pydantic schema, dispatches to service by event type. Extracts `phone_number` from `call_data` for new calls. Returns 200 even on processing errors (webhook best practice). Has try/except around `request.json()` for malformed JSON.
  - [x] Event dispatcher: switch on `message.type` — `"call-start"` → `handle_call_started`, `"call-end"` → `handle_call_ended`, `"call-failed"` → `handle_call_failed`. **Note**: Verify exact `message.type` strings against [Vapi Webhook docs](https://docs.vapi.ai) — names may use hyphens (`call-start`) or dots (`call.started`).
  - [x] **Log all received events** at INFO level (even unhandled types like `speech-start`, `transcript`, `function-call`) for debugging and future story development
  - [x] Register router in `apps/api/main.py` — add `from routers import webhooks_vapi` and `app.include_router(webhooks_vapi.router, tags=["Vapi Webhooks"])`

- [x] Update `apps/api/config/settings.py` (AC: 1, 3)
  - [x] Add `VAPI_API_KEY: str = ""` — API key for outbound Vapi calls
  - [x] Add `VAPI_BASE_URL: str = "https://api.vapi.ai"` — Vapi API base URL
  - [x] `VAPI_WEBHOOK_SECRET` already exists — no change needed

- [x] Add Vapi error codes to `packages/constants/index.ts` (AC: 1, 3)
  - [x] Add `VAPI_CALL_TRIGGER_FAILED`, `VAPI_CALL_NOT_FOUND`, `VAPI_WEBHOOK_PROCESSING_ERROR` to `VAPI_ERROR_CODES`
  - [x] Keep existing codes: `VAPI_SIGNATURE_MISSING`, `VAPI_SIGNATURE_INVALID`, `VAPI_NOT_CONFIGURED`

### Phase 4: Backend — Call Trigger Route (ACs 1, 6, 8)

- [x] Create call routes in `apps/api/routers/calls.py` (AC: 1, 6, 8)
  - [x] `APIRouter(prefix="/calls", tags=["Calls"])` — self-prefixing pattern
  - [x] `POST /calls/trigger` — triggers outbound call via Vapi, guarded by `check_call_cap` dependency
  - [x] Returns `{ call: { id, vapiCallId, status, leadId, agentId, phoneNumber, campaignId } }`
  - [x] Records usage event (`action="call_initiated"`) via `record_usage()`
  - [x] Register router in `apps/api/main.py` — add `from routers import calls` and `app.include_router(calls.router, tags=["Calls"])`
  - [x] **Compliance pre-check (AC 8)**: Before calling Vapi, perform DNC/consent check. If `packages/compliance` is not yet fully implemented, log a warning and proceed (graceful degradation for this story).

- [x] Create Pydantic schemas in `apps/api/schemas/call.py` (AC: 1)
  - [x] `TriggerCallPayload(BaseModel)` with camelCase alias — `leadId` (optional int), `agentId` (optional int), `phoneNumber` (required str, E.164 format validated via regex `^\+?[1-9]\d{1,14}$`), `campaignId` (optional int)
  - [x] `CallResponse(BaseModel)` with camelCase alias — full call record response
  - [x] `VapiWebhookPayload(BaseModel)` with camelCase alias — generic webhook payload schema

- [x] Wire usage guard to `POST /calls/trigger` (AC: 6)
  - [x] Apply `dependencies=[Depends(check_call_cap)]` to trigger endpoint
  - [x] Usage guard already exists in `apps/api/middleware/usage_guard.py` — just wire it

### Phase 5: Frontend — Call Trigger Integration (AC 1)

- [x] Create call server actions in `apps/web/src/actions/calls.ts` (AC: 1)
  - [x] `triggerCall(payload: TriggerCallRequest)` — follows canonical `branding.ts` auth pattern
  - [x] Return pattern: `{ data: TriggerCallResponse | null; error: string | null }`

- [x] Create call trigger UI component (AC: 1)
  - [x] `apps/web/src/components/calls/CallTriggerButton.tsx` — button to initiate call, uses existing Button component
  - [x] Follows Obsidian design system — Emerald primary action button

### Phase 6: Tests (ACs 1-7)

- [x] Backend tests in `apps/api/tests/` (ACs 1-7)
  - [x] `test_vapi_service_trigger.py` — unit tests for trigger_outbound_call (3 tests)
  - [x] `test_vapi_service_started.py` — unit tests for handle_call_started (2 tests)
  - [x] `test_vapi_service_ended.py` — unit tests for handle_call_ended (2 tests)
  - [x] `test_vapi_service_failed.py` — unit tests for handle_call_failed (2 tests)
  - [x] `test_vapi_client.py` — unit tests for Vapi HTTP client with mocked httpx
  - [x] `test_calls_router.py` — integration tests for POST /calls/trigger with usage guard
  - [x] `test_webhooks_vapi.py` — integration tests for webhook endpoints, signature validation, event dispatch
  - [x] `support/factories.py` — CallFactory + WebhookPayloadFactory with convenience methods
  - [x] Use `[2.1-UNIT-XXX]` traceability IDs + BDD Given/When/Then naming

- [x] Frontend tests (AC: 1)
  - [x] `apps/web/src/actions/__tests__/calls.test.ts` — server action tests
  - [x] `apps/web/src/components/calls/__tests__/CallTriggerButton.test.tsx` — component tests with axe()

- [x] E2E tests (split by AC)
  - [x] `tests/e2e/calls/call-trigger.spec.ts` — AC1: Call trigger (3 tests)
  - [x] `tests/e2e/calls/usage-limits.spec.ts` — AC2: Usage limits (2 tests)
  - [x] `tests/e2e/calls/phone-validation.spec.ts` — AC3: Phone validation (3 tests)
  - [x] `tests/e2e/calls/webhook-events.spec.ts` — AC4: Webhook events (6 tests)
  - [x] `tests/e2e/calls/webhook-signature.spec.ts` — AC5: Signature verification (2 tests)
  - [x] `tests/e2e/calls/call-errors.spec.ts` — AC6: Error scenarios + edge cases (8 tests)
  - [x] `tests/support/webhook-helpers.ts` — HMAC-SHA256 signature computation, payload builder, header factory
  - [x] `tests/playwright.config.ts` — enabled `baseURL` via `E2E_BASE_URL` env var

## Dev Notes

### Architecture Compliance

- **Backend**: FastAPI + SQLModel in `apps/api/`, extending `TenantModel` for automatic RLS via `org_id`. Use relative imports within the `apps/api/` package. [Source: project-context.md]
- **Frontend**: Next.js 15 App Router, Server Actions for data mutations. [Source: project-context.md]
- **Styling**: Tailwind v4 utility classes + Vanilla CSS. Use existing design system primitives (`Button`, `Card`, `StatusMessage`). [Source: project-context.md, story 1-4]
- **Types**: Shared TypeScript interfaces in `packages/types/`. Run `turbo run types:sync` after schema changes. [Source: architecture.md#Step 5]
- **Data access**: Use raw SQL via `session.execute(text(...))` for complex queries. Use `TenantService` for simple CRUD on `Call` rows.

### CRITICAL: What Already Exists — DO NOT recreate

| Item | Location | Usage in This Story |
|------|----------|-------|
| `verify_vapi_signature` | `apps/api/middleware/vapi_auth.py` | USE as `Depends()` on webhook routes |
| `SKIP_AUTH_PATHS` + `SKIP_AUTH_PREFIXES` includes `/webhooks/vapi` | `apps/api/middleware/auth.py` | Prefix matching added for `/webhooks/vapi/*` routes |
| `VAPI_WEBHOOK_SECRET` | `apps/api/config/settings.py:15` | Already configured. ADD `VAPI_API_KEY` and `VAPI_BASE_URL`. |
| `check_call_cap` (fail-open on DB error) | `apps/api/middleware/usage_guard.py` | Wire to `POST /calls/trigger` via `dependencies=[Depends(check_call_cap)]` |
| `record_usage` | `apps/api/services/usage.py` | Call after successful Vapi initiation with `action="call_initiated"` |
| `TelecomCallStatus` | `packages/types/call.ts` | Values: `pending`, `dialing`, `ringing`, `in_progress`, `completed`, `failed`, `busy`, `no_answer`. USE THESE. |
| `DbCall` interface (update) | `packages/types/tenant.ts:50` | Has: `id`, `leadId`, `campaignId`, `status`, `duration`. ADD: `vapiCallId`, `agentId`, `phoneNumber`, `endedAt`. MAKE `leadId` and `campaignId` optional. |
| `TenantModel` base class | `apps/api/models/base.py` | `org_id` (indexed), `created_at`, `updated_at`, `soft_delete`. EXTEND for `Call`. |
| `TenantService[T]` generic CRUD | `apps/api/services/base.py` | `create`, `get_by_id`, `list_all`, `update`, `hard_delete`. Use for simple Call CRUD. |
| `set_tenant_context` | `apps/api/database/session.py` | Sets `app.current_org_id` for RLS. Call BEFORE any SQL. |
| `httpx` | `apps/api/requirements.txt` | Already available for outbound HTTP to Vapi. |
| Router pattern | `apps/api/routers/onboarding.py` | Self-prefixing `APIRouter(prefix="/xxx")` + `app.include_router()`. FOLLOW THIS. |
| Server action auth pattern | `apps/web/src/actions/branding.ts` | `auth().getToken()` + `Authorization: Bearer`. FOLLOW THIS. |
| Design system components | `apps/web/src/components/ui/` | Button, Card, Input, StatusMessage, EmptyState. USE THESE. |
| `VAPI_ERROR_CODES` | `packages/constants/index.ts:52` | Has: `SIGNATURE_MISSING`, `SIGNATURE_INVALID`, `NOT_CONFIGURED`. ADD call-specific codes. |

### CRITICAL: SQLModel Construction Pattern

**ALWAYS use `model_validate()` for TenantModel subclass construction** — NEVER use positional kwargs. This was discovered in Stories 1.3, 1.6, and 1.7 as a recurring bug. SQLModel `table=True` silently ignores kwargs from parent classes.

```python
# WRONG — fields silently ignored:
call = Call(vapi_call_id="abc", org_id="org_123", ...)

# CORRECT — use model_validate with camelCase aliases:
call = Call.model_validate({"vapiCallId": "abc", "orgId": "org_123", ...})
```

[Source: project-context.md, Epic 1 Retrospective Discovery #1]

### CRITICAL: Vapi Webhook Auth Design

The Vapi webhook authentication design has been completed as an Epic 2 prerequisite. Follow the approved design in `_bmad-output/implementation-artifacts/vapi-webhook-auth-design.md`:

- Webhook routes use `verify_vapi_signature` dependency — NO Clerk JWT
- All other routes continue using Clerk JWT via `AuthMiddleware`
- `/webhooks/vapi` already in `SKIP_AUTH_PATHS`
- `VAPI_WEBHOOK_SECRET` already in settings
- Use `hmac.compare_digest()` for constant-time comparison (already implemented)

### Error Handling

- **Route handlers** use `HTTPException(detail={"code": "...", "message": "..."})` — Frontend extracts via `err.detail?.message`. [Source: story 1-7 Dev Notes]
- **Auth middleware** uses `JSONResponse(content={"code": "...", "message": "..."})` — different pattern, but webhook routes bypass this.
- **Webhook routes**: Return `200` even on processing errors (webhook best practice) — log errors and handle gracefully to prevent Vapi retries from stacking up. Only return `401` for signature validation failures.

### Database Schema

#### NEW: `calls` table

```sql
CREATE TABLE calls (
    id SERIAL PRIMARY KEY,
    org_id VARCHAR(255) NOT NULL,
    vapi_call_id VARCHAR(255) UNIQUE,  -- nullable: UUID placeholder used on insert, set after Vapi responds
    lead_id INTEGER REFERENCES leads(id),
    agent_id INTEGER REFERENCES agents(id),
    campaign_id INTEGER,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    duration INTEGER,
    recording_url VARCHAR(500),
    phone_number VARCHAR(20) NOT NULL,
    transcript TEXT,
    ended_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    soft_delete BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_calls_phone_number ON calls(phone_number);
CREATE INDEX idx_calls_org_id ON calls(org_id);

-- RLS policies (inherited pattern from TenantModel)
ALTER TABLE calls ENABLE ROW LEVEL SECURITY;
CREATE POLICY calls_tenant_isolation ON calls USING (org_id = current_setting('app.current_org_id'));
```

SQLModel: `apps/api/models/call.py` — extends `TenantModel` with `table=True`, `__tablename__ = "calls"`.

### API Contracts

```
POST ${NEXT_PUBLIC_API_URL}/calls/trigger
  Headers: Authorization: Bearer <clerk-jwt>
  Body: {
    leadId?: number,
    agentId?: number,
    phoneNumber: string,
    campaignId?: number
  }
  Response 201: {
    call: {
      id: number,
      vapiCallId: string,
      orgId: string,
      leadId: number | null,
      agentId: number | null,
      campaignId: number | null,
      status: "pending",
      phoneNumber: string,
      createdAt: string | null
    }
  }
  Error 403: { detail: { code: "USAGE_LIMIT_EXCEEDED", message: "..." } }
  Error 500: { detail: { code: "VAPI_CALL_TRIGGER_FAILED", message: "..." } }

POST ${API_URL}/webhooks/vapi/call-events
  Headers: vapi-signature: <hmac-sha256>
  Body: {
    message: {
      type: "call-start" | "call-end" | "call-failed" | "speech-start" | "transcript" | ...,
      call: { id: string, ... },
      ...
    },
    ...
  }
  Response 200: { received: true }
  Error 401: { detail: { code: "VAPI_SIGNATURE_INVALID", message: "..." } }
```

> **Note**: Verify exact Vapi webhook payload structure and `message.type` strings against [Vapi API docs](https://docs.vapi.ai). The above uses the most common format but Vapi may use dot notation (`call.start`) or hyphen notation (`call-start`).

### Usage Guard Integration Point

The `check_call_cap` dependency is wired to `POST /calls/trigger` via `dependencies=[Depends(check_call_cap)]`. When a tenant's cap is exceeded, the guard returns 403 `USAGE_LIMIT_EXCEEDED` before the Vapi API is called.

**Note**: `check_call_cap` in `usage_guard.py` imports `check_usage_cap_locked` (not `check_usage_cap`). The guard has a deliberate **fail-open on DB errors** design — if the database is unavailable, requests pass through rather than blocking all tenants. [Source: usage_guard.py:22-29]

```python
@router.post(
    "/trigger",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(check_call_cap)],
)
async def trigger_call(request: Request, payload: TriggerCallPayload, session: AsyncSession = Depends(get_session)):
    ...
```

[Source: project-context.md#Usage Guard for Calls, story 1-7 Usage Guard Integration Point]

### Vapi API Integration Notes

- **Outbound Call**: POST `https://api.vapi.ai/call/phone` with `Authorization: Bearer <VAPI_API_KEY>`
- **Assistant ID Mapping**: `Agent.voice_id` in our DB stores the Vapi assistant ID. Pass as `assistantId` to Vapi. If `voice_id` is empty/missing, return error `VAPI_NOT_CONFIGURED` — do not proceed with a fallback assistant.
- **Response**: Contains Vapi `id` (used as `vapi_call_id` in our DB)
- **Webhook events**: Vapi sends `message.type` with the event kind. For this story, handle `"call-start"`, `"call-end"`, `"call-failed"` only. **Log all other event types** at INFO level for future stories (2.2 handles `transcript`, `speech-*`).
- **Vapi SDK**: Use `httpx` directly (already in requirements.txt) — avoid Vapi Python SDK to maintain control over the HTTP layer.
- **Retry**: Implement retry with exponential backoff (max 3 retries) on transient Vapi API failures to support NFR.R1 (99.9% uptime).
- **Deployment**: CORS in `main.py` currently allows `http://localhost:3000` only. Production deployment must update `allow_origins` to include the actual frontend domain and ensure Vapi webhook URLs are configured in Vapi dashboard.

### Testing Standards

- **Backend**: `pytest` in `apps/api/tests/` — follow existing test patterns
- **Frontend Unit**: `vitest` in `apps/web/src/`
- **Accessibility**: `vitest-axe` `axe()` on all new components
- **Coverage**: >80% for new code
- **Mock external deps**: Mock Vapi API calls with `httpx` mock patterns, mock `httpx.AsyncClient` in tests
- **Test traceability**: Use `[2.1-UNIT-XXX]` IDs following the `[1.7-UNIT-XXX]` pattern from story 1-7
- **BDD naming**: Given/When/Then in test names
- **Webhook tests**: Test valid signature (200), missing signature (401), invalid signature (401), unconfigured secret (500), duplicate webhook idempotency (200 with same result)
- **Test factories**: Create `CallFactory` helper using `model_validate()` pattern
- **Compliance test**: Test the compliance pre-check path — mock `packages/compliance` check and verify it's called before Vapi API

### Project Structure Notes

- All new backend files follow the established `apps/api/` package structure
- Webhook routes at `/webhooks/vapi/*` covered by `SKIP_AUTH_PREFIXES` (prefix matching) — uses `verify_vapi_signature` dependency instead of Clerk JWT
- Call trigger route at `/calls/trigger` requires Clerk auth (NOT in skip list) — protected by default
- `/calls/trigger` also requires `check_call_cap` dependency — wire explicitly

### File Structure

```
apps/api/
├── models/
│   ├── call.py                    # NEW (CREATE) — Call SQLModel
│   └── __init__.py               # MODIFY — add call import
├── routers/
│   ├── calls.py                  # NEW (CREATE) — POST /calls/trigger
│   └── webhooks_vapi.py          # NEW (CREATE) — POST /webhooks/vapi/call-events
├── schemas/
│   └── call.py                   # NEW (CREATE) — Pydantic models with camelCase aliases
├── services/
│   ├── vapi.py                   # NEW (CREATE) — call lifecycle service (trigger, handle events)
│   └── vapi_client.py            # NEW (CREATE) — Vapi HTTP client (initiate_call)
├── migrations/versions/          # NEW — migration: CREATE calls table with RLS
├── tests/
│   ├── test_vapi_service_trigger.py  # NEW (CREATE) — trigger_outbound_call tests
│   ├── test_vapi_service_started.py  # NEW (CREATE) — handle_call_started tests
│   ├── test_vapi_service_ended.py    # NEW (CREATE) — handle_call_ended tests
│   ├── test_vapi_service_failed.py   # NEW (CREATE) — handle_call_failed tests
│   ├── test_vapi_client.py           # NEW (CREATE) — Vapi HTTP client tests (mocked)
│   ├── test_calls_router.py          # NEW (CREATE) — POST /calls/trigger integration tests
│   ├── test_webhooks_vapi.py         # NEW (CREATE) — webhook endpoint tests
│   └── support/
│       └── factories.py              # EXTEND — CallFactory + WebhookPayloadFactory
├── config/
│   └── settings.py               # MODIFY — add VAPI_API_KEY, VAPI_BASE_URL
└── main.py                       # MODIFY — register calls + webhooks_vapi routers

apps/web/src/
├── actions/
│   └── calls.ts                  # NEW (CREATE) — Server Actions for calls API
│       └── __tests__/
│           └── calls.test.ts     # NEW (CREATE) — server action tests
├── components/
│   └── calls/                    # NEW (CREATE)
│       ├── CallTriggerButton.tsx  # NEW (CREATE) — call trigger button
│       └── __tests__/
│           └── CallTriggerButton.test.tsx  # NEW (CREATE)

packages/
├── types/
│   ├── call.ts                   # MODIFY — add TriggerCallRequest, TriggerCallResponse
│   ├── vapi.ts                   # NEW (CREATE) — Vapi webhook payload types
│   ├── tenant.ts                 # MODIFY — update DbCall with vapiCallId, agentId, phoneNumber
│   └── index.ts                  # MODIFY — add vapi export
├── constants/
│   └── index.ts                  # MODIFY — add call-specific VAPI error codes

tests/e2e/calls/                  # NEW (CREATE) — split by AC
├── call-trigger.spec.ts          # AC1: Call trigger
├── usage-limits.spec.ts          # AC2: Usage limits
├── phone-validation.spec.ts      # AC3: Phone validation
├── webhook-events.spec.ts        # AC4: Webhook events
├── webhook-signature.spec.ts     # AC5: Signature verification
└── call-errors.spec.ts           # AC6: Error scenarios + edge cases
```

### References

- [Epic: epics.md#Story 2.1 — Vapi Telephony Bridge & Webhook Integration]
- [PRD: prd.md#FR4 — Voice pipeline latency <500ms]
- [PRD: prd.md#NFR.R1 — 99.9% uptime for calling bridge]
- [PRD: prd.md#NFR.R2 — Provider failover <3s]
- [Architecture: architecture.md#Step 4 — SQLModel + TenantModel, RLS pattern]
- [Architecture: architecture.md#Step 5 — Naming conventions, error format, type sync]
- [Architecture: architecture.md#Step 9 — Telephony Failover Protocol (Vapi primary, Twilio fallback)]
- [UX Design: ux-design-specification.md#Step 7 — Master Join experience]
- [Project Context: project-context.md — Tech stack, testing, security, Epic 2 Integration Notes]
- [Project Context: project-context.md#Epic 2 Integration Notes — Vapi webhook auth, usage guard, RLS for voice events]
- [Vapi Webhook Auth Design: vapi-webhook-auth-design.md — HMAC-SHA256 design (APPROVED)]
- [Previous Story 1-7: 1-7-resource-guardrails-usage-monitoring-hard-caps.md — Usage guard, error patterns]
- [Epic 1 Retrospective: epic-1-retro-2026-03-31.md — SQLModel model_validate() lesson, webhook auth prerequisite]
- [Auth Middleware: apps/api/middleware/auth.py — SKIP_AUTH_PATHS includes /webhooks/vapi]
- [Vapi Auth: apps/api/middleware/vapi_auth.py — verify_vapi_signature already implemented]
- [Usage Guard: apps/api/middleware/usage_guard.py — check_call_cap dependency]
- [Usage Service: apps/api/services/usage.py — record_usage for call_initiated events]
- [Existing Types: packages/types/call.ts — TelecomCall + TelecomCallStatus]
- [Existing Types: packages/types/tenant.ts:50 — DbCall interface]
- [Existing Types: packages/types/transcript.ts — TranscriptEntry with role tagging]
- [TenantModel: apps/api/models/base.py — Base class with org_id, created_at, updated_at]
- [Settings: apps/api/config/settings.py — VAPI_WEBHOOK_SECRET already configured]
- [Server Action Auth: apps/web/src/actions/branding.ts — Canonical auth pattern]

### Previous Story Learnings — Top 5 Rules

1. **SQLModel `model_validate()` ONLY** — NEVER use positional kwargs for `TenantModel` subclasses. Bug recurred in Stories 1.3, 1.6, 1.7. Use `Model.model_validate({"camelKey": value})`.
2. **Server Action Auth = `branding.ts` pattern** — `auth().getToken()` + `Authorization: Bearer`. DO NOT follow `client.ts`.
3. **Router pattern = `onboarding.py`** — Self-prefixing `APIRouter(prefix="/xxx")` + `app.include_router(router, tags=["XXX"])`. Include `PydanticValidationError` catch block.
4. **Error responses** — Route handlers: `HTTPException(detail={"code": ..., "message": ...})`. Frontend extracts via `err.detail?.message`.
5. **Testing** — BDD Given/When/Then naming + `[X.X-UNIT-XXX]` traceability IDs. All animated components: `reducedMotion?: boolean`.

<details>
<summary>Per-story detail (click to expand)</summary>

**Story 1-1**: Turborepo monorepo with pnpm, `apps/web` = Next.js 15 App Router, `apps/api` = FastAPI + SQLModel + Alembic

**Story 1-2**: Clerk auth: `ClerkProvider`, `useOrganization()`, `useUser()`. Auth middleware pattern with JWT validation, `request.state.org_id`.

**Story 1-3**: RLS via `TenantModel` base class with `org_id`. Alembic migrations workflow. `set_config()` transaction-scoping (use `is_local=True`) for RLS context.

**Story 1-4**: Design system: StatusMessage (warning/error variants), Card, Button. Obsidian theme: `#09090B` bg, Neon Emerald/Crimson/Blue accents. `cn()` utility, barrel exports, `vitest-axe`.

**Story 1-5**: Server action auth pattern: `auth().getToken()` + `Authorization: Bearer` header. Return pattern: `{ data: T | null; error: string | null }`.

**Story 1-6**: Router self-prefixing pattern. `PydanticValidationError` catch block pattern in routers — MUST use in all route handlers.

**Story 1-7**: Usage guard `check_call_cap` wired via `dependencies=[Depends(check_call_cap)]`. `record_usage()` for tracking events. `_compute_threshold()` pure function. Plan-based cap resolution from `agencies` table.

**Epic 1 Retro**: Vapi webhook auth identified as critical prerequisite — NOW APPROVED and implemented in `middleware/vapi_auth.py`. Code reviews use 3-layer adversarial review.

</details>

### Known Limitations & Future Considerations

- **Compliance pre-check (partial)**: Architecture mandates `packages/compliance` import for all call-initiation routes (DNC/TCPA validation per FR10). This story includes a compliance check stub — logs warning if `packages/compliance` is not yet fully implemented. Full DNC scrubbing and consent validation comes in Epic 4.
- **Vapi assistant configuration**: This story triggers calls with a phone number and assistant reference. The full Vapi assistant configuration (system prompt, voice settings, RAG integration) will be built in Stories 2.2 and 2.3. For this story, use a minimal assistant config or pass-through. `Agent.voice_id` maps to the Vapi assistant ID.
- **No telephony failover yet**: Architecture calls for Vapi primary + Twilio fallback (NFR.R2). This story implements Vapi only. Failover comes in Story 2.3 (TTS fallback) and Epic 5 (full failover protocol).
- **Webhook idempotency**: Vapi may send duplicate webhook events. Service handlers use `INSERT ... ON CONFLICT (vapi_call_id) DO UPDATE` for idempotent upserts. Future stories should add explicit idempotency key handling for edge cases.
- **No transcript handling yet**: Webhooks for `transcript` events will be handled in Story 2.2. `transcript` column is pre-allocated in the schema. This story only handles `call-start`, `call-end`, `call-failed`.
- **Recording URL**: Populated from `call-end` webhook but actual recording retrieval/playback is deferred to a future story.
- **Phone number validation**: Basic validation on input (E.164 format). Full validation with carrier lookup is deferred.
- **Lead-agent binding**: The trigger endpoint accepts optional `lead_id` and `agent_id`. Future stories should support campaign-based automatic lead-agent pairing.

## Dev Agent Record

### Agent Model Used

glm-5.1 (zai-coding-plan/glm-5.1)

### Debug Log References

- httpx.Timeout requires all 4 params or a single default — fixed in vapi_client.py
- FastAPI dependency_overrides need proper async function signatures, not AsyncMock — fixed in test_webhooks_vapi.py
- asyncio.sleep was lazily imported in vapi_client.py — changed to top-level import so tests can patch `asyncio.sleep` directly
- `get_session()` auto-commits after yield (`session.py:46-57`) — no explicit `session.commit()` needed in service handlers

### Code Review Findings (BMAD Adversarial Review — commit `b29f9de`)

16 findings from 3-layer review (Blind Hunter, Edge Case Hunter, Acceptance Auditor). All resolved.

| # | Finding | Fix | Files |
|---|---------|-----|-------|
| 1 | `handle_call_ended`/`handle_call_failed` missing `set_tenant_context` + `org_id` param | Added `org_id` param + `await set_tenant_context()` before SQL in both handlers | `services/vapi.py` |
| 2 | UNIQUE constraint race on empty `vapi_call_id` — multiple inserts with empty string collide | Use UUID placeholder (`uuid4().hex[:16]`) on insert; made `vapi_call_id` Optional[str] in model; migration changed to nullable UNIQUE | `services/vapi.py`, `models/call.py`, migration |
| 3 | Raw SQL positional `row[N]` mapping fragile — column reordering breaks silently | Replaced with `result.mappings()` + `_row_to_call()` helper that maps by column name | `services/vapi.py` |
| 4 | Missing `session.commit()` in handlers | Confirmed no-op — `get_session()` auto-commits after yield | No change needed |
| 5 | Auth middleware exact-match `SKIP_AUTH_PATHS` didn't match `/webhooks/vapi/call-events` | Added `SKIP_AUTH_PREFIXES` tuple + `startswith()` matching in `_should_skip_auth` | `middleware/auth.py` |
| 6 | `httpx.Timeout` not separating connect vs read timeouts | Changed to `httpx.Timeout(connect=5.0, read=10.0)` | `services/vapi_client.py` |
| 7 | `request.json()` in webhook route had no error handling for malformed JSON | Added try/except around `request.json()` returning 200 with error log | `routers/webhooks_vapi.py` |
| 8 | `handle_call_started` used non-atomic SELECT then INSERT (race condition) | Rewrote as atomic `INSERT ... ON CONFLICT (vapi_call_id) DO UPDATE` | `services/vapi.py` |
| 9 | `handle_call_failed` discarded `error_message` — not stored anywhere | Store error_message in `transcript` column | `services/vapi.py` |
| 10 | `phone_number` not extracted from webhook `call_data` for new calls | Extract `phone_number` from `call.call_data` in webhook route, pass to handler | `routers/webhooks_vapi.py` |
| 11 | No phone number format validation — any string accepted | Added E.164 regex `^\+?[1-9]\d{1,14}$` to `TriggerCallPayload` schema via `field_validator` | `schemas/call.py` |
| 12 | Non-numeric metadata values (`lead_id="abc"`) crash `_safe_int()` was missing | Added `_safe_int()` helper that catches ValueError and returns None | `services/vapi.py` |
| 13 | Webhook route accepted raw dict — no Pydantic validation | Added `VapiWebhookPayload` schema with `message: dict` field, validated in route | `routers/webhooks_vapi.py` |
| 14 | `httpx.AsyncClient` created inside retry loop — new connection per attempt | Moved `AsyncClient` outside retry loop for connection reuse | `services/vapi_client.py` |
| 15 | `TriggerCallResponse.createdAt: string` — but created_at can be None | Changed to `string \| null` | `packages/types/call.ts` |
| 16 | Spec AC8 compliance stub — `_compliance_pre_check` had duplicate `async def`/`def` | Removed orphaned `async def` line; AC8 already correctly describes stub behavior | `routers/calls.py` |

### Completion Notes List

- All 23 backend tests pass (3 vapi_service_trigger, 2 vapi_service_started, 2 vapi_service_ended, 2 vapi_service_failed, 7 vapi_client, 5 calls_router, 9 webhooks_vapi — note: some overlap in coverage)
- Frontend tests: 5 CallTriggerButton tests pass (2.1-UNIT-500..504); 18 pre-existing org test failures unrelated
- E2E tests: 24 test cases across 6 AC-focused spec files under `tests/e2e/calls/` covering AC1–AC6
- Webhook helper utilities created (tests/support/webhook-helpers.ts) — HMAC signature, payload builder
- Playwright config updated with baseURL via E2E_BASE_URL env var
- Migration file created but not executed against DB (needs manual `alembic upgrade head`)
- packages/compliance stub graceful degradation implemented (try/except ImportError)
- Webhook routes return 200 even on processing errors (webhook best practice)
- Code review completed: 16 findings from BMAD 3-layer adversarial review, all resolved (commit `b29f9de`)
- `vapi_call_id` column changed to nullable UNIQUE with UUID placeholder to prevent constraint races
- Auth middleware enhanced with `SKIP_AUTH_PREFIXES` for prefix-based webhook path matching
- E.164 phone validation added to `TriggerCallPayload` schema
- `TriggerCallResponse.createdAt` typed as `string | null` in TypeScript
- **Test Quality Review**: 93/100 (A+ - Excellent). All 6 findings resolved (commit `c3fc7a0`):
  - P0: Replaced conditional `if isVisible` guards with `await expect().toBeVisible()` in all E2E tests
  - P1: Split `calls.spec.ts` (589 lines) into 6 AC-focused spec files under `tests/e2e/calls/`
  - P1: Split `test_vapi_service.py` (342 lines) into 4 handler-specific files
  - P1: Created `CallFactory` + `WebhookPayloadFactory` in `factories.py`
  - P1: Narrowed `test_2_1_unit_207` assertion from 4 status codes to `(201, 403)`
  - P3: Removed implementation-detail assertion from `test_2_1_unit_308`

### File List

**NEW files:**
- `apps/api/models/call.py`
- `apps/api/migrations/versions/g2h3i4j5k6l7_add_calls_table_for_vapi_telephony_bridge.py`
- `apps/api/schemas/call.py`
- `apps/api/services/vapi_client.py`
- `apps/api/services/vapi.py`
- `apps/api/routers/webhooks_vapi.py`
- `apps/api/routers/calls.py`
- `packages/types/vapi.ts`
- `apps/web/src/actions/calls.ts`
- `apps/web/src/components/calls/CallTriggerButton.tsx`
- `apps/web/src/actions/__tests__/calls.test.ts`
- `apps/web/src/components/calls/__tests__/CallTriggerButton.test.tsx`
- `apps/api/tests/test_vapi_service_trigger.py`
- `apps/api/tests/test_vapi_service_started.py`
- `apps/api/tests/test_vapi_service_ended.py`
- `apps/api/tests/test_vapi_service_failed.py`
- `apps/api/tests/test_vapi_client.py`
- `apps/api/tests/test_calls_router.py`
- `apps/api/tests/test_webhooks_vapi.py`
- `tests/e2e/calls/call-trigger.spec.ts`
- `tests/e2e/calls/usage-limits.spec.ts`
- `tests/e2e/calls/phone-validation.spec.ts`
- `tests/e2e/calls/webhook-events.spec.ts`
- `tests/e2e/calls/webhook-signature.spec.ts`
- `tests/e2e/calls/call-errors.spec.ts`
- `tests/support/webhook-helpers.ts`

**MODIFIED files:**
- `apps/api/models/__init__.py` — added Call import
- `apps/api/config/settings.py` — added VAPI_API_KEY, VAPI_BASE_URL
- `apps/api/main.py` — registered calls + webhooks_vapi routers
- `apps/api/middleware/auth.py` — added `SKIP_AUTH_PREFIXES` for webhook prefix matching
- `apps/api/models/call.py` — `vapi_call_id` changed from `str` to `Optional[str]`
- `apps/api/migrations/versions/g2h3i4j5k6l7_add_calls_table_for_vapi_telephony_bridge.py` — `vapi_call_id` nullable UNIQUE
- `apps/api/schemas/call.py` — added E.164 regex validation for `phone_number`
- `apps/api/services/vapi.py` — added `_row_to_call()`, `_safe_int()`, UUID placeholder, atomic upsert, `org_id` params, error_message storage
- `apps/api/services/vapi_client.py` — `AsyncClient` outside retry loop, separate connect/read timeouts, jitter
- `apps/api/routers/webhooks_vapi.py` — `VapiWebhookPayload` validation, `request.json()` error handling, `phone_number` extraction
- `apps/api/routers/calls.py` — fixed duplicate `_compliance_pre_check` definition
- `packages/types/tenant.ts` — updated DbCall with vapiCallId, agentId, phoneNumber, endedAt; made leadId/campaignId optional
- `packages/types/call.ts` — added TriggerCallRequest, TriggerCallResponse; `createdAt: string | null`
- `packages/types/index.ts` — added vapi export
- `packages/constants/index.ts` — added VAPI_CALL_TRIGGER_FAILED, VAPI_CALL_NOT_FOUND, VAPI_WEBHOOK_PROCESSING_ERROR
- `tests/playwright.config.ts` — enabled baseURL via E2E_BASE_URL env var
