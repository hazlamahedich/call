---
stepsCompleted:
  - step-01-preflight
  - step-02-select-framework
  - step-03-scaffold-framework
  - step-04-docs-and-scripts
lastStep: step-04-docs-and-scripts
lastSaved: 2026-03-31T16:46:02+08:00
story: 2.1
framework: playwright
---

# Test Framework Progress — Story 2.1: Vapi Telephony Bridge & Webhook Integration

## Preflight Results

- **Project type:** Fullstack (Next.js 15 + FastAPI)
- **Detected stack:** `fullstack`
- **Bundler:** pnpm monorepo with Turborepo
- **Existing framework:** Playwright already installed at `tests/`
- **Config:** `tests/playwright.config.ts` (chromium, firefox, webkit)

## Framework Selection

Playwright (already initialized). Enhanced config with `baseURL`.

## Scaffolded Artifacts

### `tests/support/webhook-helpers.ts` (NEW)

HMAC-SHA256 webhook signature computation and payload builder:

- `computeVapiSignature(body)` — computes HMAC using `VAPI_WEBHOOK_SECRET`
- `buildWebhookPayload(eventType, overrides)` — constructs valid Vapi webhook JSON
- `webhookHeaders(body)` — returns headers map with `vapi-signature`

### `tests/e2e/calls.spec.ts` (REWRITTEN)

**24 unique test cases** across 8 describe blocks, ×3 browsers = **72 total test entries**.

| Describe Block                 | AC  | Tests | Priority |
| ------------------------------ | --- | ----- | -------- |
| Call Trigger                   | AC1 | 3     | P0       |
| Usage Limit Enforcement        | AC2 | 2     | P0/P1    |
| Phone Number Validation        | AC3 | 3     | P0/P1    |
| Webhook: call-start            | AC4 | 2     | P0/P1    |
| Webhook: call-end              | AC4 | 2     | P0/P1    |
| Webhook: call-failed           | AC4 | 2     | P0/P1    |
| Webhook Signature Verification | AC5 | 2     | P0       |
| Webhook Edge Cases             | AC6 | 5     | P1/P2    |
| API Error Scenarios            | AC6 | 3     | P1       |

### `tests/playwright.config.ts` (UPDATED)

- Enabled `baseURL` via `E2E_BASE_URL` env var (defaults to `http://127.0.0.1:3000`)

## Coverage Map

### Frontend Tests (require running web app + Clerk)

| Test ID     | What                              | Auth Required             |
| ----------- | --------------------------------- | ------------------------- |
| 2.1-E2E-001 | Call trigger button → API call    | Yes (`authenticatedPage`) |
| 2.1-E2E-002 | Trigger response field validation | Yes                       |
| 2.1-E2E-003 | Lead/agent context preservation   | Yes                       |
| 2.1-E2E-010 | Usage limit exceeded error        | Yes                       |
| 2.1-E2E-011 | Usage warning threshold           | Yes                       |
| 2.1-E2E-080 | 500 VAPI_NOT_CONFIGURED           | Yes                       |
| 2.1-E2E-081 | 500 generic trigger failure       | Yes                       |
| 2.1-E2E-082 | 403 AUTH_FORBIDDEN                | Yes                       |

### API-Only Tests (direct HTTP, no web app needed)

| Test ID     | What                                   | Requires    |
| ----------- | -------------------------------------- | ----------- |
| 2.1-E2E-020 | Invalid phone format → 422             | Running API |
| 2.1-E2E-021 | Empty phone → 422                      | Running API |
| 2.1-E2E-022 | E.164 without auth → 401/403           | Running API |
| 2.1-E2E-030 | call-start webhook → 200               | Running API |
| 2.1-E2E-031 | call-start with metadata → 200         | Running API |
| 2.1-E2E-040 | call-end with duration/recording → 200 | Running API |
| 2.1-E2E-041 | call-end without optionals → 200       | Running API |
| 2.1-E2E-050 | call-failed with error → 200           | Running API |
| 2.1-E2E-051 | call-failed without error → 200        | Running API |
| 2.1-E2E-060 | Missing signature → 401                | Running API |
| 2.1-E2E-061 | Invalid signature → 401                | Running API |
| 2.1-E2E-070 | Missing call ID → 200                  | Running API |
| 2.1-E2E-071 | Missing org_id → 200                   | Running API |
| 2.1-E2E-072 | Unknown event type → 200               | Running API |
| 2.1-E2E-073 | Malformed JSON → 200                   | Running API |
| 2.1-E2E-074 | Duplicate webhook (idempotent) → 200×2 | Running API |

## Environment Variables

| Variable              | Purpose                       | Default                 |
| --------------------- | ----------------------------- | ----------------------- |
| `E2E_BASE_URL`        | Web app base URL              | `http://127.0.0.1:3000` |
| `NEXT_PUBLIC_API_URL` | API base URL (used in spec)   | `http://localhost:8000` |
| `E2E_CLERK_EMAIL`     | Clerk test user email         | —                       |
| `E2E_CLERK_PASSWORD`  | Clerk test user password      | —                       |
| `VAPI_WEBHOOK_SECRET` | HMAC secret for webhook tests | `test-webhook-secret`   |
