# Story 1.6: 10-Minute Launch Onboarding Wizard

Status: review
As a New User,
I want a 5-Question onboarding ritual,
so that I can set up my first AI agent and begin dialing in under 10 minutes.

## Acceptance Criteria

1. **Onboarding Entry**: Given a freshly created Client sub-account, when the user logs in for the first time, then they are automatically redirected to the "Zen" onboarding flow (5-question wizard). [Source: epics.md#Story 1.6]

2. **5-Question Wizard**: Given the onboarding flow, when the user proceeds through the wizard, then they are guided through exactly 5 questions: (1) business goal, (2) primary script context, (3) voice selection, (4) integration choice, and (5) safety level. [Source: epics.md#Story 1.6]

3. **Auto-Creation of Records**: Given the user completes all 5 wizard steps, when the wizard finishes, then the system automatically creates the first `Agent` record and `Script` record in the database, scoped to the user's tenant via `org_id`. [Source: epics.md#Story 1.6]

4. **Progress Visualization**: Given the onboarding flow is active, when the user advances between steps, then a minimalist "status bridge" progress indicator shows current position (step N of 5) with completed steps visually distinct. [Source: epics.md#Story 1.6, UX-DR13]

5. **Zen-to-Obsidian Transition**: Given the wizard completes, when all records are created, then the UI transitions from the minimalist "Zen" onboarding mode to the "Obsidian" cockpit using the System Boot Ritual (`CockpitContainer` boot animation). [Source: ux-design-specification.md#Step 9 §1.3]

6. **Onboarding Completion Flag**: Given the user has completed onboarding, when they log in again, then they are NOT redirected to the wizard (onboarding is tracked as complete per-tenant). [Source: PRD#10-Minute Promise]

## Tasks / Subtasks

### Phase 1: Backend — Data Models & API (ACs 3, 6)

- [x] Register onboarding error codes in `packages/constants/index.ts` (AC: 3, 6)
  - [x] Add `ONBOARDING_ERROR_CODES` object with `as const` pattern matching existing `AUTH_ERROR_CODES` / `TENANT_ERROR_CODES`
  - [x] Codes: `ONBOARDING_ALREADY_COMPLETE`, `ONBOARDING_VALIDATION_ERROR`, `ONBOARDING_CREATE_ERROR`
  - [x] Export derived type `OnboardingErrorCode`

- [x] Create `Agent` SQLModel in `apps/api/models/agent.py` (AC: 3)
  - [x] Fields: `id`, `org_id`, `name`, `voice_id`, `business_goal`, `safety_level`, `integration_type`, `onboarding_complete` (bool, default False), `created_at`, `updated_at`, `soft_delete`
  - [x] Extends `TenantModel` with `table=True`, `__tablename__ = "agents"` (inherits `org_id`, timestamps, RLS via base class)
  - [x] Register in `apps/api/models/__init__.py`
  - [x] Generate Alembic migration as part of the single combined migration (see below)

- [x] ALTER existing `scripts` table — NO new SQLModel file needed (AC: 3)
  - [x] **CRITICAL:** The `scripts` table already exists in migration `eb48e89c217f` with base columns (`id`, `org_id`, `created_at`, `updated_at`, `soft_delete`) and full RLS policies. DO NOT create a new `Script` SQLModel file.
  - [x] Create `apps/api/models/script.py` that extends `TenantModel` with `table=True`, `__tablename__ = "scripts"` — adds columns: `agent_id` (int, FK → agents.id), `name` (str, default "Initial Script"), `content` (str, default ""), `version` (int, default 1), `script_context` (str, default "")
  - [x] Register in `apps/api/models/__init__.py`
  - [x] Generate Alembic migration as part of the single combined migration (see below)

- [x] Generate single combined Alembic migration (AC: 3)
  - [x] After creating BOTH `agent.py` and `script.py` SQLModel files and registering them, run ONE command: `alembic revision --autogenerate -m "add agents and extend scripts"`
  - [x] Verify the generated migration contains: CREATE TABLE `agents` + ALTER TABLE `scripts` (add columns only)
  - [x] If autogenerate tries to CREATE the `scripts` table, manually edit the migration to only ALTER TABLE

- [x] Add TypeScript interfaces to `packages/types/` (AC: 3)
  - [x] Create `packages/types/agent.ts` — `Agent` interface matching backend model with camelCase aliases
  - [x] Create `packages/types/onboarding.ts` — `OnboardingPayload` interface (single typed object for all wizard data: `businessGoal`, `scriptContext`, `voiceId`, `integrationType`, `safetyLevel`) + `OnboardingStatus` interface (`{ completed: boolean }`)
  - [x] **DO NOT create `packages/types/script.ts`** — a `Script` type already exists in `packages/types/tenant.ts` (not barrel-exported). Instead, extend the existing type definition or import directly from `tenant.ts` where needed. This avoids a naming collision.
  - [x] Add exports to `packages/types/index.ts` — add `agent`, `onboarding`. The `tenant` re-export already exists at line 7, no action needed.
  - [x] Run `turbo run types:sync`

- [x] Update existing `DbScript` interface in `packages/types/tenant.ts` (AC: 3)
  - [x] The `scripts` table is gaining `agent_id` and `script_context` columns (see ALTER TABLE above). The existing `DbScript` interface at line 58 must be updated to reflect this.
  - [x] Add `agentId?: number` (FK → agents, optional because existing rows won't have it)
  - [x] Add `scriptContext?: string` (new column with default `""`, optional for backward compat)
  - [x] Final `DbScript` interface:
    ```typescript
    export interface DbScript extends TenantScoped {
      id: number;
      name: string;
      content: string;
      version: number;
      agentId?: number;
      scriptContext?: string;
    }
    ```

- [x] Create onboarding API routes in `apps/api/routers/onboarding.py` (AC: 3, 6)
  - [x] Use `APIRouter(prefix="/onboarding")` — self-prefixing pattern matching existing `webhooks.py`
  - [x] `POST /onboarding/complete` — accepts `OnboardingPayload`, creates `Agent` + updates `Script` records in a single transaction, sets `onboarding_complete=True` on agent
  - [x] `GET /onboarding/status` — returns `OnboardingStatus` by checking if any Agent with `onboarding_complete=True` exists for the tenant
  - [x] Auth context pattern: access `org_id` via `request.state.org_id` (set by `AuthMiddleware`). Use `Request` parameter in route handlers:
    ```python
    @router.post("/complete")
    async def complete_onboarding(request: Request, payload: OnboardingPayload):
        org_id = request.state.org_id  # Set by AuthMiddleware from Clerk JWT
    ```
  - [x] Register router in `apps/api/main.py`: `app.include_router(onboarding.router, tags=["Onboarding"])`

- [x] Create Pydantic `OnboardingPayload` model in `apps/api/schemas/onboarding.py` (AC: 3)
  - [x] Define `OnboardingPayload` as a Pydantic `BaseModel` with fields: `business_goal: str`, `script_context: str`, `voice_id: str`, `integration_type: str`, `safety_level: str`
  - [x] Use `AliasGenerator(to_camel)` to match the camelCase JSON keys from the frontend (consistent with `TenantModel` aliasing)
  - [x] Import and use in the onboarding router's `POST /complete` handler: `async def complete_onboarding(request: Request, payload: OnboardingPayload)`
  - [x] Add field validators: `safety_level` must be one of the allowed levels, `script_context` minimum 20 characters (matching frontend validation)

- [x] Write backend tests (AC: 3, 6)
  - [x] `tests/test_onboarding.py` — test successful Agent+Script creation, test duplicate onboarding prevention, test RLS (tenant A cannot see tenant B's onboarding status)
  - [x] Coverage target: >80%

### Phase 2: Frontend — Wizard UI (ACs 1, 2, 4)

- [x] Create onboarding constants in `apps/web/src/lib/onboarding-constants.ts`
  - [x] Define `BUSINESS_GOALS`, `VOICE_OPTIONS`, `INTEGRATION_OPTIONS`, `SAFETY_LEVELS` as typed constant arrays
  - [x] These will be shared between wizard components and backend validation (future Epics 2/6)
  - [x] Each option: `{ id: string, name: string, description: string }`
  - [x] Voice and integration placeholder data lives here (actual Vapi/CRM integration in Epic 2/6)

- [x] Create onboarding page at `apps/web/src/app/(onboarding)/onboarding/page.tsx` (AC: 1, 2)
  - [x] Multi-step wizard with 5 steps managed by state
  - [x] Each step is a distinct sub-component for testability
  - [x] Uses "Zen" minimalist aesthetic: high whitespace, low density (per UX Step 9 §1.2)
  - [x] OBSIDIAN THEME: `bg-background` (`#09090B`), Geist Sans for labels, muted Zinc for non-active elements
  - [x] Accept `reducedMotion` prop and pass to animated child components (progress indicator, CockpitContainer)
  - [x] Wizard step validation: "Next" button disabled until valid selection/input is provided per step

- [x] Create step components in `apps/web/src/components/onboarding/` (AC: 2)
  - [x] `StepBusinessGoal.tsx` — Step 1: Select business goal. Renders `BUSINESS_GOALS` from constants. Use Card components with selection state. Validates: one must be selected to proceed.
  - [x] `StepScriptContext.tsx` — Step 2: Primary script context (textarea). Character count indicator. Validates: minimum 20 characters to proceed. Shows helper text "Describe your product, service, or offer in a few sentences."
  - [x] `StepVoiceSelection.tsx` — Step 3: Voice selection. Renders `VOICE_OPTIONS` from constants. Each voice card shows name + short description. Validates: one must be selected to proceed.
  - [x] `StepIntegrationChoice.tsx` — Step 4: Integration choice. Renders `INTEGRATION_OPTIONS` from constants. Use Card selection pattern. Validates: one must be selected (includes "Skip for now" default option).
  - [x] `StepSafetyLevel.tsx` — Step 5: Safety level. Renders `SAFETY_LEVELS` from constants. Each option explains compliance features. Validates: one must be selected. Default: "Strict (recommended)".
  - [x] All step components: keyboard-accessible Card selection (Enter/Space to toggle), ARIA labels for screen readers

- [x] Create progress indicator component (AC: 4)
  - [x] `OnboardingProgress.tsx` — Minimalist status bridge: 5 dots connected by lines. Active step = Emerald (`#10B981`), completed = Emerald filled, upcoming = Zinc muted. Current step label shown below.
  - [x] Accept `reducedMotion?: boolean` prop — when true, skip dot transition animations

- [x] Create onboarding Server Actions (AC: 3)
  - [x] `apps/web/src/actions/onboarding.ts` — Server Actions following the `branding.ts` auth pattern:
    ```typescript
    "use server";
    import { auth } from "@clerk/nextjs/server";
    import type { Agent, OnboardingPayload, OnboardingStatus } from "@call/types";

    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    ```
  - [x] `completeOnboarding(wizardData: OnboardingPayload)` — calls `${NEXT_PUBLIC_API_URL}/onboarding/complete` with `Authorization: Bearer <token>` header. **Auth pattern**: `const { getToken } = await auth(); const token = await getToken();` (matching `apps/web/src/actions/branding.ts`). Return pattern: `{ agent: Agent | null; error: string | null }`.
  - [x] `getOnboardingStatus()` — calls `${NEXT_PUBLIC_API_URL}/onboarding/status` with auth header. Returns `{ data: OnboardingStatus | null; error: string | null }`. Does NOT take `orgId` parameter — `org_id` is resolved server-side from the JWT via `request.state.org_id`.

### Phase 3: Flow Logic & Redirects (ACs 1, 5, 6)

- [x] Add onboarding redirect logic (AC: 1, 6)
  - [x] **MODIFY** `apps/web/src/app/(dashboard)/dashboard/layout.tsx` — this file already exists with `BrandingProvider` + `DashboardHeader` wrapping. Add onboarding redirect logic **while preserving** the existing `BrandingProvider` + `DashboardHeader` structure from Story 1-5.
  - [x] Add a client-side onboarding guard component (e.g., `OnboardingGuard`) that wraps `{children}` inside the existing layout. The guard checks onboarding status on mount.
  - [x] In the guard, use `useOrganization()` from `@clerk/nextjs` to get `org_id`
  - [x] Check `getOnboardingStatus(orgId)` on mount
  - [x] While checking status, render a skeleton/loading state to prevent flash of dashboard content (see UX section below)
  - [x] If `completed === false` → `router.push("/onboarding")`
  - [x] If `completed === true` → render `{children}` (dashboard content)
  - [x] **DO NOT overwrite or remove** the existing `BrandingProvider` + `DashboardHeader` wrapper. The onboarding redirect is an ADDITION to the existing layout, not a replacement.
  - [x] Also add `/onboarding(.*)` to the Clerk protected route matcher in `apps/web/src/middleware.ts` so unauthenticated users cannot access the wizard directly.

- [x] Create `apps/web/src/app/(onboarding)/layout.tsx` — minimal "Zen" layout (AC: 1)
  - [x] No sidebar, no fleet navigator — clean, high-whitespace wrapper
  - [x] Centered content with max-width constraint
  - [x] Geist Sans typography, Obsidian background (`bg-background`)
  - [x] This is a **separate route group** from `(dashboard)` with its own layout

- [x] Implement Zen-to-Obsidian transition (AC: 5)
  - [x] After `completeOnboarding` succeeds, trigger `CockpitContainer` boot animation
  - [x] Use `active` prop + `onBootComplete` callback to transition to the main dashboard
  - [x] The transition should feel like the "System Boot Ritual" (grid scan + neon ignition per UX Step 9 §1.3)
  - [x] Pass `reducedMotion` prop to `CockpitContainer` to respect user preferences

### Phase 4: Tests (ACs 1-6)

- [x] Frontend unit tests in `apps/web/src/components/onboarding/__tests__/` (AC: 2, 4)
  - [x] `StepBusinessGoal.test.tsx` — renders 4 goal options, selection updates state
  - [x] `StepScriptContext.test.tsx` — textarea renders, character count works, validates min length
  - [x] `StepVoiceSelection.test.tsx` — renders voice cards, selection toggles
  - [x] `StepIntegrationChoice.test.tsx` — renders integration options, selection works
  - [x] `StepSafetyLevel.test.tsx` — renders safety levels with descriptions, selection works
  - [x] `OnboardingProgress.test.tsx` — renders 5 dots, correct step highlighted
  - [x] Accessibility: `axe()` on each step, all interactive elements keyboard-navigable

- [x] Integration test for full wizard flow (AC: 1, 5, 6)
  - [x] Test wizard step navigation: Next/Back buttons advance/regress correctly
  - [x] Test completion calls Server Action with correct payload
  - [x] Test redirect away from `/onboarding` after completion

## Dev Notes

### Architecture Compliance

- **Backend**: FastAPI + SQLModel in `apps/api/`, extending `TenantModel` for automatic RLS via `org_id`. Use relative imports within the `apps/api/` package (matching `webhooks.py` pattern: `from ..models.agent import Agent`, not absolute imports). [Source: project-context.md]
- **Frontend**: Next.js 15 App Router, Server Actions for data mutations, `"use client"` for wizard interactivity. [Source: project-context.md]
- **Styling**: Tailwind v4 utility classes + Vanilla CSS. Use existing design system primitives (`Button`, `Card`, `Input`, `StatusMessage`). [Source: project-context.md, story 1-4]
- **Types**: Shared TypeScript interfaces in `packages/types/`. Run `turbo run types:sync` after schema changes. [Source: architecture.md#Step 5]
- **Data access**: Use SQLModel session directly in route handlers for onboarding CRUD (transactional Agent+Script creation). If a service layer pattern emerges in future stories, refactor accordingly. The `request.state.org_id` from `AuthMiddleware` provides tenant context — no separate service class needed for the onboarding endpoint's scoped operations.
- **Auto-redirect decision**: The epics describe a user-initiated flow ("starts the Zen flow"). This story extends that with a system-initiated auto-redirect for first-time users (checking `onboarding_complete` flag). This ensures no user lands on an empty dashboard — a practical UX decision that doesn't conflict with the epic intent.

### CRITICAL: What Already Exists — DO NOT recreate

| Item | Location | Notes |
|------|----------|-------|
| Design system components | `apps/web/src/components/ui/` | Button, Card, Input, StatusMessage, EmptyState, ConfirmAction, FocusIndicator, Dialog, Tooltip, Popover, ScrollArea, Tabs, Switch — USE THESE |
| Obsidian signature components | `apps/web/src/components/obsidian/` | CockpitContainer (boot animation with `active` + `onBootComplete` + `reducedMotion` props), VibeBorder, ContextTriad, GlitchPip, TelemetryStreamObsidian — USE CockpitContainer for AC 5 |
| `cn()` utility | `apps/web/src/lib/utils.ts` | `clsx` + `tailwind-merge` |
| Clerk auth | `apps/web/src/app/layout.tsx` | `ClerkProvider` wraps app, `useOrganization()` gives `org_id` |
| Tenant-scoped base model | `apps/api/models/base.py` | `TenantModel` with `org_id` (indexed), `created_at`, `updated_at`, `soft_delete`. Uses `AliasGenerator(to_camel)` for camelCase JSON. |
| Auth middleware | `apps/api/middleware/auth.py` | Validates Clerk JWT (RS256 via JWKS), sets `request.state.org_id` and `request.state.user_id`. Skips `/health`, `/docs`, `/openapi.json`, `/webhooks/clerk`. |
| Backend routers | `apps/api/routers/` | `health.py` (tags=["Health"]), `webhooks.py` (`APIRouter(prefix="/webhooks")`, tags=["Webhooks"]) — add `onboarding.py` following SAME pattern: self-prefixing `APIRouter(prefix="/onboarding")` + `app.include_router(onboarding.router, tags=["Onboarding"])` |
| Alembic migrations | `apps/api/migrations/versions/` | Single migration `eb48e89c217f` creates 8 tables WITH RLS (agents, **scripts**, leads, calls, agencies, clients, campaigns, knowledge_bases, usage_logs). **`scripts` table ALREADY EXISTS** — only ALTER it. |
| Test infrastructure | `apps/web/vitest.config.ts` | jsdom env, setup file (`vitest.setup.ts`), path aliases (`@` → `./src`). |
| Server actions pattern | `apps/web/src/actions/branding.ts` | Auth pattern: `const { getToken } = await auth(); const token = await getToken(); headers: { Authorization: \`Bearer ${token}\` }`. Return `{ data: T \| null; error: string \| null }`. FOLLOW THIS PATTERN for onboarding actions — do NOT use the older `client.ts` pattern which lacks auth headers. |
| Error constants pattern | `packages/constants/index.ts` | `AUTH_ERROR_CODES`, `TENANT_ERROR_CODES` — `as const` + derived type union. Add `ONBOARDING_ERROR_CODES` following SAME pattern. |
| Next.js middleware | `apps/web/src/middleware.ts` | Clerk middleware — currently protects `/dashboard(.*)` and `/api/trpc/(.*)`. ADD `/onboarding(.*)` to the protected route matcher. |
| Dashboard layout | `apps/web/src/app/(dashboard)/dashboard/layout.tsx` | **ALREADY EXISTS** — wraps children in `<BrandingProvider>` + `<DashboardHeader>`. DO NOT overwrite — add `OnboardingGuard` as a wrapper inside this existing structure. |
| Existing types | `packages/types/tenant.ts` | Has `Script` type (NOT barrel-exported). Has `Lead`, `Agency`, `Client`, `Campaign`, `Call`, `UsageLog`, `DbScript` — **DO NOT create duplicate `Script` type**. UPDATE `DbScript` to add `agentId` and `scriptContext` fields. |

### UX Design Requirements

- **"Zen" Onboarding Mode**: Minimalist, high-whitespace, low-density layout. This is the OPPOSITE of the "Command Center" density. Think clean form, not tactical dashboard. [Source: ux-design-specification.md#Step 9 §1.2]
- **Drag-and-Drop KB Ingestion**: NOT part of this story. KB ingestion is Epic 3 (Story 3.1). Step 2 (Script Context) is a simple textarea only. [Source: PRD — KB is Phase 1 but separate epic]
- **5-Question Wizard**: The UX spec references a "5-Question Wizard" within the 10-Minute Launch flow. The 5 questions are defined in the epics: business goal, primary script context, voice selection, integration choice, safety level. [Source: epics.md#Story 1.6]
- **System Boot Ritual**: On completion, the CockpitContainer's `active` prop triggers the boot animation (grid scan + neon ignition). This transitions from "Zen" to "Obsidian" mode. [Source: ux-design-specification.md#Step 9 §1.3]
- **Progress Bridge**: Minimalist visual — 5 dots with connecting lines, NOT a full progress bar. Emerald for active/completed, Zinc for upcoming. [Source: UX-DR13, ux-design-specification.md#Step 9]
- **`reducedMotion` prop**: All animated components (OnboardingProgress, CockpitContainer, wizard step transitions) must accept `reducedMotion?: boolean`. When true, disable dot transitions, grid scan, and neon ignition animations — show static state immediately. [Source: story 1-4 — `reducedMotion` prop pattern on all animated components]
- **`reducedMotion` source**: Detect via `window.matchMedia('(prefers-reduced-motion: reduce)')` in the wizard page component (`apps/web/src/app/(onboarding)/onboarding/page.tsx`) and pass the boolean down to all animated children. Do not call `matchMedia` inside individual components — centralize the detection once at the page level.
- **Wizard state persistence**: When users navigate Back/Forward between steps, all previously entered data must be retained. Use React state (lifted to the wizard page orchestrator) — do NOT use URL params or localStorage for this. State lives in the parent wizard component and is passed down as props to each step.
- **Submission error recovery**: If `completeOnboarding` fails, display an error message with a "Try Again" button. Do NOT clear the wizard state or reset to Step 1. The user should be able to retry from Step 5 without re-entering data.

### Voice & Integration Placeholder Data

Voice and integration options are **UI placeholders** only — actual Vapi voice mapping is Epic 2, CRM integration is Epic 6. All option arrays are defined in `apps/web/src/lib/onboarding-constants.ts` as typed constants with shape `{ id: string; name: string; description: string }`.

- **`VOICE_OPTIONS`**: 4 placeholder voices (Avery, Jordan, Casey, Morgan) — store selected `voice_id` string in `Agent` record
- **`INTEGRATION_OPTIONS`**: 3 options (GoHighLevel, HubSpot, "Skip for now" default) — store selected `integration_type` in `Agent` record
- **`BUSINESS_GOALS`**: Goal categories for Step 1 — each has `id`, `name`, `description`
- **`SAFETY_LEVELS`**: Safety/compliance levels for Step 5 — includes "Strict (recommended)" default

Step components import their options from this constants file. Do NOT inline option arrays in component files.

### Database Schema

#### NEW: `agents` table (CREATE TABLE)

This table does NOT exist yet. Migration creates it with full RLS:

```sql
CREATE TABLE agents (
    id SERIAL PRIMARY KEY,
    org_id TEXT NOT NULL,
    name VARCHAR(255) NOT NULL DEFAULT 'My First Agent',
    voice_id VARCHAR(100) NOT NULL,
    business_goal VARCHAR(255) NOT NULL,
    safety_level VARCHAR(50) NOT NULL DEFAULT 'strict',
    integration_type VARCHAR(100),
    onboarding_complete BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    soft_delete BOOLEAN NOT NULL DEFAULT FALSE
);

-- RLS enabled automatically by TenantModel base class
-- Policy: tenant_isolation_agents — USING (org_id = current_setting('app.current_org_id'))
```

SQLModel: `apps/api/models/agent.py` — extends `TenantModel` with `table=True`, `__tablename__ = "agents"`.

#### EXISTING: `scripts` table (ALTER TABLE — add columns)

The `scripts` table already exists in migration `eb48e89c217f` with base columns (`id`, `org_id`, `created_at`, `updated_at`, `soft_delete`) and full RLS policies. **DO NOT create a new table.** Only add new columns:

```sql
ALTER TABLE scripts
    ADD COLUMN agent_id INTEGER REFERENCES agents(id),
    ADD COLUMN name VARCHAR(255) NOT NULL DEFAULT 'Initial Script',
    ADD COLUMN content TEXT NOT NULL DEFAULT '',
    ADD COLUMN version INTEGER NOT NULL DEFAULT 1,
    ADD COLUMN script_context TEXT NOT NULL DEFAULT '';
```

SQLModel: `apps/api/models/script.py` — extends `TenantModel` with `table=True`, `__tablename__ = "scripts"`. Alembic autogenerate may try to CREATE TABLE — if so, manually edit the migration to only ALTER TABLE.

**Migration note**: Generate with `alembic revision --autogenerate -m "add agents and extend scripts"`. Verify the generated migration contains one CREATE TABLE (`agents`) and one ALTER TABLE (`scripts` — add columns only).

### API Contracts

Backend routes use `APIRouter(prefix="/onboarding")` (self-prefixing, matching `webhooks.py` pattern). Auth context is accessed via `request.state.org_id` and `request.state.user_id` (set by `AuthMiddleware` from Clerk JWT).

```python
# Route handler pattern (apps/api/routers/onboarding.py)
@router.post("/complete")
async def complete_onboarding(request: Request, payload: OnboardingPayload):
    org_id = request.state.org_id   # Set by AuthMiddleware
    user_id = request.state.user_id  # Set by AuthMiddleware
    ...
```

Frontend server actions call `${NEXT_PUBLIC_API_URL}/onboarding/...` (no `/api/` prefix — the router self-prefixes `/onboarding`).

```
POST ${NEXT_PUBLIC_API_URL}/onboarding/complete
  Headers: Authorization: Bearer <clerk-jwt>
  Body: {
    businessGoal: string,      // from step 1
    scriptContext: string,     // from step 2
    voiceId: string,           // from step 3
    integrationType: string,   // from step 4
    safetyLevel: string        // from step 5
  }
  Response 201: {
    agent: { id, orgId, name, voiceId, businessGoal, ... },
    script: { id, orgId, agentId, name, content, ... }
  }
  Response 400: { code: "ONBOARDING_ALREADY_COMPLETE", message: "..." }

GET ${NEXT_PUBLIC_API_URL}/onboarding/status
  Headers: Authorization: Bearer <clerk-jwt>
  Response 200: { completed: boolean }
```

### Onboarding Redirect Pattern

**CRITICAL**: `apps/web/src/app/(dashboard)/dashboard/layout.tsx` already exists with `BrandingProvider` + `DashboardHeader` (from Story 1-5). You must **MODIFY** it — do NOT overwrite or recreate. Add an onboarding guard while preserving the existing wrapper.

The existing layout structure (preserve this):
```tsx
// apps/web/src/app/(dashboard)/dashboard/layout.tsx — CURRENT STATE
"use client";
import { BrandingProvider } from "@/lib/branding-context";
import { DashboardHeader } from "@/components/dashboard-header";

export default function DashboardLayout({ children }) {
  return (
    <BrandingProvider>
      <div className="flex min-h-screen flex-col">
        <DashboardHeader />
        <main className="flex-1">{children}</main>
      </div>
    </BrandingProvider>
  );
}
```

Add an `OnboardingGuard` component and integrate it into the existing layout:

```tsx
// apps/web/src/components/onboarding-guard.tsx — NEW file
"use client";
import { useOrganization } from "@clerk/nextjs";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getOnboardingStatus } from "@/actions/onboarding";

export function OnboardingGuard({ children }: { children: React.ReactNode }) {
  const { organization } = useOrganization();
  const router = useRouter();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    if (!organization) { setChecking(false); return; }
    getOnboardingStatus(organization.id).then(({ data }) => {
      if (data && !data.completed) {
        router.push("/onboarding");
      } else {
        setChecking(false);
      }
    });
  }, [organization, router]);

  if (checking) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        {/* Skeleton loader — prevents flash of dashboard content */}
        <div className="animate-pulse space-y-4 w-full max-w-md px-4">
          <div className="h-8 bg-muted rounded w-1/3" />
          <div className="h-4 bg-muted rounded w-2/3" />
          <div className="h-32 bg-muted rounded" />
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
```

```tsx
// apps/web/src/app/(dashboard)/dashboard/layout.tsx — MODIFIED
"use client";
import { BrandingProvider } from "@/lib/branding-context";
import { DashboardHeader } from "@/components/dashboard-header";
import { OnboardingGuard } from "@/components/onboarding-guard";

export default function DashboardLayout({ children }) {
  return (
    <BrandingProvider>
      <OnboardingGuard>
        <div className="flex min-h-screen flex-col">
          <DashboardHeader />
          <main className="flex-1">{children}</main>
        </div>
      </OnboardingGuard>
    </BrandingProvider>
  );
}
```

The `checking` state + skeleton prevents the flash of dashboard content during the onboarding status check. Only after the check resolves does the guard either redirect or render children.

Also add `/onboarding(.*)` to the protected route matcher in `apps/web/src/middleware.ts`:

```typescript
// apps/web/src/middleware.ts — MODIFIED
const isProtectedRoute = createRouteMatcher([
  "/dashboard(.*)",
  "/onboarding(.*)",  // ← ADD: prevent unauthenticated wizard access
  "/api/trpc/(.*)",
]);
```

The `/onboarding` route itself is a separate route group `(onboarding)` with its own minimal "Zen" layout (no sidebar, no fleet navigator).

### Error Handling

- **Error response format**: Use flat `{ code: string, message: string }` at the top level. This matches the actual codebase convention used in auth middleware and other existing routes. The architecture spec documents a nested `{ error: { code, message } }` format, but the implementation uses flat — follow the implementation.
- **FastAPI error responses**: Return `JSONResponse(status_code=4xx, content={ "code": "ERROR_CODE", "message": "Human readable" })` from route handlers. This is consistent with how other routes handle errors.
- Register onboarding error codes in `packages/constants/index.ts` following the existing `as const` pattern:

```typescript
// packages/constants/index.ts — ADD to existing file
export const ONBOARDING_ERROR_CODES = {
  ONBOARDING_ALREADY_COMPLETE: "ONBOARDING_ALREADY_COMPLETE",
  ONBOARDING_VALIDATION_ERROR: "ONBOARDING_VALIDATION_ERROR",
  ONBOARDING_CREATE_ERROR: "ONBOARDING_CREATE_ERROR",
} as const;

export type OnboardingErrorCode =
  (typeof ONBOARDING_ERROR_CODES)[keyof typeof ONBOARDING_ERROR_CODES];
```

This matches the existing `AUTH_ERROR_CODES` and `TENANT_ERROR_CODES` pattern already in the file.

### Testing Standards

- **Backend**: `pytest` in `apps/api/tests/test_onboarding.py` — follow existing test patterns from RLS tests
- **Frontend Unit**: `vitest` in `apps/web/src/components/onboarding/__tests__/`
- **Accessibility**: `vitest-axe` `axe()` on all step components — every Card selection must be keyboard-accessible (Enter/Space to select)
- **Coverage**: >80% for new code
- **Mock external deps**: Mock API calls in frontend tests, use test database for backend tests
- **Per-step validation tests**: Each step component test must verify the "Next" button is disabled when input is invalid and enabled when valid (e.g., no selection made, textarea below min length)
- **`reducedMotion` prop test**: `OnboardingProgress.test.tsx` must verify that when `reducedMotion={true}`, no transition animations play (render static state immediately). Test `CockpitContainer` similarly in the integration flow test.
- **Test traceability**: Use `[1.6-UNIT-XXX]` IDs following the `[1.4-UNIT-XXX]` pattern from story 1-4. BDD Given/When/Then naming convention for test descriptions.

### File Structure

```
apps/api/
├── models/
│   ├── agent.py              # NEW (CREATE) — Agent SQLModel
│   ├── script.py             # NEW (CREATE) — Script SQLModel (extends existing table)
│   └── __init__.py           # MODIFY — add agent, script imports
├── routers/
│   └── onboarding.py         # NEW (CREATE) — onboarding endpoints, APIRouter(prefix="/onboarding")
├── schemas/
│   └── onboarding.py         # NEW (CREATE) — Pydantic OnboardingPayload model with camelCase aliases
├── migrations/versions/      # NEW — single migration: CREATE agents + ALTER scripts
├── tests/
│   └── test_onboarding.py    # NEW (CREATE) — backend tests
└── main.py                   # MODIFY — register onboarding router

apps/web/src/
├── app/
│   ├── (onboarding)/         # NEW — route group with Zen layout
│   │   ├── layout.tsx        # NEW (CREATE) — minimal Zen layout (no sidebar)
│   │   └── onboarding/
│   │       └── page.tsx      # NEW (CREATE) — wizard orchestrator
│   └── (dashboard)/
│       └── dashboard/
│           └── layout.tsx    # MODIFY — add OnboardingGuard to existing BrandingProvider + DashboardHeader layout
├── components/
│   ├── onboarding-guard.tsx  # NEW (CREATE) — client-side onboarding redirect guard with loading skeleton
│   └── onboarding/           # NEW (CREATE) — wizard step components
│       ├── index.ts
│       ├── StepBusinessGoal.tsx
│       ├── StepScriptContext.tsx
│       ├── StepVoiceSelection.tsx
│       ├── StepIntegrationChoice.tsx
│       ├── StepSafetyLevel.tsx
│       ├── OnboardingProgress.tsx    # accepts reducedMotion prop
│       └── __tests__/
│           ├── StepBusinessGoal.test.tsx
│           ├── StepScriptContext.test.tsx
│           ├── StepVoiceSelection.test.tsx
│           ├── StepIntegrationChoice.test.tsx
│           ├── StepSafetyLevel.test.tsx
│           └── OnboardingProgress.test.tsx
├── actions/
│   └── onboarding.ts         # NEW (CREATE) — Server Actions for onboarding
├── middleware.ts              # MODIFY — add /onboarding(.*) to protected routes
├── lib/
│   └── onboarding-constants.ts  # NEW (CREATE) — VOICE_OPTIONS, INTEGRATION_OPTIONS, BUSINESS_GOALS, SAFETY_LEVELS

packages/
├── types/
│   ├── agent.ts              # NEW (CREATE) — Agent interface
│   ├── onboarding.ts         # NEW (CREATE) — OnboardingPayload + OnboardingStatus interfaces
│   ├── tenant.ts             # MODIFY — add agentId + scriptContext to DbScript interface
│   └── index.ts              # MODIFY — add agent, onboarding exports (tenant re-export already exists)
├── constants/
│   └── index.ts              # MODIFY — add ONBOARDING_ERROR_CODES with as const pattern
```

### References

- [Epic: epics.md#Epic 1 — Story 1.6: 10-Minute Launch Onboarding Wizard]
- [PRD: prd.md#The 10-Minute Promise — onboarding flow requirements]
- [UX Onboarding Flow: ux-design-specification.md#Step 10 §1.1 — wizard flow details]
- [UX Design Direction: ux-design-specification.md#Step 9 §1.2 — Zen mode aesthetic; §1.3 — System Boot Ritual transition]
- [UX Components: ux-design-specification.md#Step 11 — CockpitContainer boot animation API (`active`, `onBootComplete`, `reducedMotion`)]
- [UX Design Direction UX-DR13: ux-design-specification.md — Progress bridge visual spec (5 dots + connecting lines)]
- [Architecture: architecture.md#Step 4 — SQLModel + TenantModel, RLS pattern, Clerk auth flow]
- [Architecture: architecture.md#Step 5 — Naming conventions (camelCase aliases), error response format, type sync]
- [Project Context: project-context.md — Tech stack (Next.js 15, FastAPI, Tailwind v4), testing (vitest, pytest), security]
- [Previous Story 1-4: 1-4-obsidian-design-system-foundation-reusable-components.md — Design system components, reducedMotion pattern, test patterns, barrel export convention]
- [Backend Models: apps/api/models/base.py — TenantModel base class with `org_id`, `AliasGenerator(to_camel)`]
- [Backend Auth: apps/api/middleware/auth.py — Clerk JWT validation (RS256 via JWKS), sets `request.state.org_id` + `request.state.user_id`]
- [Backend Router Pattern: apps/api/routers/webhooks.py — `APIRouter(prefix="/webhooks")` self-prefixing pattern]
- [Existing Migration: apps/api/migrations/versions/eb48e89c217f — Creates 8 tables including `scripts` with RLS]
- [Frontend Server Actions: apps/web/src/actions/branding.ts — Auth pattern with `auth().getToken()` and `Authorization: Bearer` header]
- [Frontend Server Actions (older pattern): apps/web/src/actions/client.ts — Return pattern `{ data: T | null; error: string | null }` but lacks auth headers — DO NOT follow this pattern]
- [Error Constants: packages/constants/index.ts — `as const` + derived type pattern (`AUTH_ERROR_CODES`, `TENANT_ERROR_CODES`)]
- [Type Collision: packages/types/tenant.ts — Existing `Script` type (NOT barrel-exported) — DO NOT duplicate. UPDATE `DbScript` to add `agentId`, `scriptContext`]
- [Dashboard Layout: apps/web/src/app/(dashboard)/dashboard/layout.tsx — ALREADY EXISTS with `BrandingProvider` + `DashboardHeader` — ADD `OnboardingGuard`, do NOT overwrite]
- [Branding Actions: apps/web/src/actions/branding.ts — Correct server action auth pattern using `auth().getToken()`]

### Previous Story Learnings

**From Story 1-1:**
- Turborepo monorepo established with pnpm
- `apps/web` = Next.js 15 App Router + Tailwind v4
- `apps/api` = FastAPI + SQLModel + Alembic

**From Story 1-2:**
- Clerk auth integrated: `ClerkProvider`, `useOrganization()`, `useUser()`
- Dashboard pages use `useOrganization().id` for tenant context
- `lucide-react` icons available
- `class-variance-authority` (CVA) available for component variants

**From Story 1-3:**
- RLS fully implemented: `TenantModel` base class with `org_id` auto-populated
- Backend tests use test database with RLS verification
- Alembic migrations workflow established

**From Story 1-4:**
- Full design system available: Button, Card, Input, StatusMessage, EmptyState, ConfirmAction, Dialog, Tooltip, Popover, ScrollArea, Tabs, Switch
- Obsidian components: CockpitContainer (with `active` prop + `onBootComplete` callback + `reducedMotion` prop for boot animation)
- Testing: `vitest-axe` for accessibility, Vitest with jsdom env, `@testing-library/user-event`
- Pattern: `"use client"` directive on interactive components
- Pattern: Barrel exports via `index.ts` in component directories
- Pattern: `cn()` utility from `@/lib/utils` for className composition
- Pattern: `reducedMotion?: boolean` prop on all animated components — must propagate to child animations
- Pattern: Server actions return `{ data: T | null; error: string | null }` (see `apps/web/src/actions/client.ts`)
- Pattern: `vitest-axe` — use `axe()` from `vitest-axe` for accessibility testing on all components
- Tailwind v4 design tokens in `globals.css` (background, border, neon colors, glassmorphism)
- Test traceability: `[1.4-UNIT-XXX]` IDs, BDD Given/When/Then naming
- Test results: 26 test suites, 217 tests passing — all new code must maintain this baseline
- Barrel export status: `packages/types/tenant.ts` IS re-exported from `packages/types/index.ts` (line 7) — no action needed when adding new type exports

## Dev Agent Record

### Agent Model Used

zai-coding-plan/glm-5.1

### Debug Log References

- Backend test fixes: model_validate requires camelCase keys due to TenantModel AliasGenerator(to_camel)
- Frontend test fixes: userEvent.type fires per-character in controlled components; OnboardingProgress needed aria-label for WCAG compliance
- Router update: Added ONBOARDING_VALIDATION_ERROR usage via explicit PydanticValidationError catch block
- **Test automation expansion**: SQLModel `table=True` constructor silently ignores kwargs — must use `model_validate()` with camelCase aliases or `setattr()` for test factories
- **Bug fix**: `apps/web/src/actions/onboarding.ts` was truncated at 19 lines with broken syntax (`import { API_URL }` instead of `const API_URL =`). Reconstructed with complete `getOnboardingStatus()` and `completeOnboarding()` functions.
- **Test fix**: UNIT-075 back-navigation assertion corrected — `fillThroughStep3()` advances to step 4, so Back goes to step 3 not step 2

### Completion Notes List

1. All 18 backend unit tests pass (schema validation, error code sync, model tests)
2. All 9 backend route integration tests pass (POST /complete happy/idempotency/auth/error/validation, GET /status completed/not-completed/auth/sql-verification)
3. All 52 frontend unit tests pass (5 step components + OnboardingProgress + StepBusinessGoal + OnboardingGuard + OnboardingPage, each with axe accessibility audit, keyboard navigation tests)
4. 8 E2E Playwright tests written (7 require Clerk auth fixtures, 1 unauthenticated redirect)
5. Alembic migration f1g2h3i4j5k6 handles CREATE agents + ALTER scripts in single migration
6. OnboardingGuard wraps existing BrandingProvider+DashboardHeader in dashboard layout (not overwritten)
7. /onboarding(.*) added to Clerk protected route matcher in middleware.ts
8. Zen layout created as separate (onboarding) route group from (dashboard)
9. **Test automation summary**: `_bmad-output/test-artifacts/story-1-6-automation-summary.md`

### File List

**Backend (NEW):**
- apps/api/models/agent.py
- apps/api/models/script.py
- apps/api/schemas/__init__.py
- apps/api/schemas/onboarding.py
- apps/api/routers/onboarding.py
- apps/api/migrations/versions/f1g2h3i4j5k6_add_agents_and_extend_scripts.py
- apps/api/tests/test_onboarding.py
- apps/api/tests/test_onboarding_router.py

**Backend (MODIFIED):**
- apps/api/models/__init__.py
- apps/api/main.py

**Frontend (NEW):**
- apps/web/src/lib/onboarding-constants.ts
- apps/web/src/components/onboarding/StepBusinessGoal.tsx
- apps/web/src/components/onboarding/StepScriptContext.tsx
- apps/web/src/components/onboarding/StepVoiceSelection.tsx
- apps/web/src/components/onboarding/StepIntegrationChoice.tsx
- apps/web/src/components/onboarding/StepSafetyLevel.tsx
- apps/web/src/components/onboarding/OnboardingProgress.tsx
- apps/web/src/components/onboarding/index.ts
- apps/web/src/components/onboarding-guard.tsx
- apps/web/src/actions/onboarding.ts
- apps/web/src/app/(onboarding)/layout.tsx
- apps/web/src/app/(onboarding)/onboarding/page.tsx
- apps/web/src/components/onboarding/__tests__/StepBusinessGoal.test.tsx
- apps/web/src/components/onboarding/__tests__/StepScriptContext.test.tsx
- apps/web/src/components/onboarding/__tests__/StepVoiceSelection.test.tsx
- apps/web/src/components/onboarding/__tests__/StepIntegrationChoice.test.tsx
- apps/web/src/components/onboarding/__tests__/StepSafetyLevel.test.tsx
- apps/web/src/components/onboarding/__tests__/OnboardingProgress.test.tsx
- apps/web/src/components/__tests__/onboarding-guard.test.tsx
- apps/web/src/app/(onboarding)/onboarding/__tests__/page.test.tsx

**Frontend (MODIFIED):**
- apps/web/src/app/(dashboard)/dashboard/layout.tsx
- apps/web/src/middleware.ts

**E2E (NEW):**
- tests/e2e/onboarding.spec.ts

**Shared Packages (MODIFIED):**
- packages/constants/index.ts
- packages/types/agent.ts (NEW)
- packages/types/onboarding.ts (NEW)
- packages/types/tenant.ts
- packages/types/index.ts

### Change Log

| Date       | Action                                                      |
|------------|-------------------------------------------------------------|
| 2026-03-30 | Story status: ready-for-dev → review. All tasks completed.  |
| 2026-03-30 | Backend: 18/18 tests passing. Frontend: 26/26 tests passing. |
| 2026-03-30 | Test automation expansion: +43 tests (9 backend integration, 26 frontend unit, 8 E2E). Fixed truncated onboarding.ts. Backend: 27/27 tests (18 unit + 9 integration). Frontend: 52/52 tests (320 total suite). |
