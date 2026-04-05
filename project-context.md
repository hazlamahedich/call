---
project_name: "call"
user_name: "team mantis a"
date: "2026-03-17"
sections_completed:
  ["technology_stack", "language_rules", "testing", "security"]
existing_patterns_found: 10
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

- **Monorepo Management**: Turborepo (latest), pnpm (10.26.1)
- **Frontend Framework**: Next.js 15 (App Router strictly)
- **Backend Framework**: FastAPI (latest), Python 3.x
- **ORM / Data Layer**: SQLModel, PostgreSQL 17 (Neon)
- **Authentication**: Clerk (Organization-aware)
- **UI Design System**: "Obsidian" (Obsidian Black `#09090B`, Neon sign accents), Radix UI
- **Testing**: Playwright (E2E), Pytest (Backend)
- **Telephony**: Vapi (Unified Voice Engine)

## Critical Implementation Rules

### Language & Framework Specifics

**Python (FastAPI / SQLModel)**

- Use `snake_case` for all functions, variables, and internal logic.
- Prefer `async def` for all route handlers and database-touching methods.
- **Naming Alignment**: Use `AliasGenerator` (pydantic) to strictly map `camelCase` (JSON API) to `snake_case` (Python logic).
- **Error Handling**: Standardize JSON responses using `packages/constants`.

**TypeScript (Next.js 15)**

- Use `camelCase` for variables/functions and `PascalCase` for React components.
- **Client-Server Boundary**: Use **Server Actions** (`"use server"`) as the primary pattern for data mutations and fetching where appropriate; minimize ad-hoc API route creation.
- **Imports**: Mandatory absolute path aliases (e.g., `@/components/...`).
- **Styles**: Use Vanilla CSS for all custom UI components.

### Testing & Quality

- **Unit Testing**: All new features must have >80% coverage in `pytest` (backend) or `vitest` (web).
- **E2E Testing**: Critical paths (Auth, Call Creation, Dashboard) required in Playwright.
- **Latency Guardrails**:
  - Voice Pipeline: <500ms
  - RAG/Context retrieval: <200ms
- **Validation**: Implement 'latency-aware' tests in Pytest that fail if performance thresholds are breached.
- **Mocking**: Always mock external AI streams (Vapi, Cartesia) during E2E/Unit testing to ensure deterministic results.

### Database & Security

- **Multi-tenancy**: Strict PostgreSQL Row Level Security (RLS) on all tables using `jwt.org_id` from Clerk.
- **Optimization**: Every multi-tenant query MUST use indices that include `org_id` to prevent performance degradation.
- **Authentication**: Clerk organization-aware tokens must be validated in every request.
- **SQLModel Construction**: ALWAYS use `Model.model_validate({"camelKey": value})` — NEVER use `Model(field=value)` positional kwargs. SQLModel `table=True` silently ignores kwargs from parent classes. This applies to all `TenantModel` subclasses. See: `_bmad-output/implementation-artifacts/1-3-*.md` Discovery #2.
- **Barrel Exports**: Every `.ts` file in `packages/types/` MUST be re-exported from `packages/types/index.ts`. After creating any new type file, add `export * from "./filename"` to the index.

### Server Action Auth Pattern (CANONICAL)

All Server Actions that call the FastAPI backend MUST authenticate using Clerk tokens. The canonical pattern (established in `apps/web/src/actions/branding.ts`):

```typescript
import { auth } from "@clerk/nextjs/server";

export async function myAction(): Promise<{
  data: T | null;
  error: string | null;
}> {
  try {
    const { getToken } = await auth();
    const token = await getToken();
    if (!token) return { data: null, error: "Not authenticated" };

    const response = await fetch(`${API_URL}/endpoint`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    // ... error handling with err.detail?.message extraction
  } catch (e) {
    return { data: null, error: (e as Error).message };
  }
}
```

Key requirements:

- Use `auth()` from `@clerk/nextjs/server` (NOT `useAuth()` — that's client-side only)
- Always pass `Authorization: Bearer <token>` header to API calls
- Extract errors via `err.detail?.message` (backend uses `HTTPException(detail={...})`)
- Return `{ data: T | null; error: string | null }` pattern
- DO NOT follow the older pattern in `client.ts` or `organization.ts` which lacks auth headers

### Monorepo Layout

- `apps/web`: Next.js frontend.
- `apps/api`: FastAPI backend.
- `packages/types`: Shared TypeScript interfaces.
- `packages/compliance`: DNC/TCPA logic.
- `packages/constants`: Shared error codes and registry.

### AI Provider Abstraction

The project uses a **configurable single-provider pattern** for both embeddings and LLM:

- **Setting**: `AI_PROVIDER` in `config/settings.py` (`"openai"` or `"gemini"`)
- **Embedding**: `services/embedding/providers/` — `EmbeddingProvider` ABC with `OpenAIEmbeddingProvider` and `GeminiEmbeddingProvider`, instantiated via `EmbeddingProviderFactory.create()`
- **LLM**: `services/llm/providers/` — `LLMProvider` ABC with `OpenAILLMProvider` and `GeminiLLMProvider`, instantiated via `LLMProviderFactory.create()`
- **Per-Org Overrides**: `models/ai_provider_settings.py` stores Fernet-encrypted API keys and model preferences per organization. Managed via `routers/ai_settings.py` and frontend at `/dashboard/settings/ai-providers`
- **Dimension Config**: `AI_EMBEDDING_DIMENSIONS` in settings; `knowledge_chunk.py` uses `settings.AI_EMBEDDING_DIMENSIONS` instead of hardcoded values
- **Adding a new provider**: Create a new `*_provider.py` in both `embedding/providers/` and `llm/providers/`, implement the ABC, register in the factory

**Key files**:

- `apps/api/config/settings.py` — `AI_PROVIDER`, `AI_EMBEDDING_MODEL`, `AI_EMBEDDING_DIMENSIONS`, `AI_LLM_MODEL`, etc.
- `apps/api/services/embedding/` — Embedding provider abstraction
- `apps/api/services/llm/` — LLM provider abstraction
- `apps/api/models/ai_provider_settings.py` — Per-org config model
- `apps/api/routers/ai_settings.py` — Settings API endpoints
- `apps/web/src/actions/ai-providers.ts` — Frontend server actions
- `packages/types/ai-provider.ts` — Shared TypeScript types

### Epic 2 Integration Notes

- **Vapi Webhook Auth**: Epic 2 introduces Vapi telephony webhooks (server-to-server). These cannot use Clerk JWT. Design must support API-key or HMAC-based auth for `/webhooks/vapi/*` routes. Add Vapi routes to the auth middleware skip list (`SKIP_AUTH_PATHS` in `apps/api/middleware/auth.py`).
- **Usage Guard for Calls**: `check_call_cap` dependency in `apps/api/middleware/usage_guard.py` must be wired to `POST /calls/trigger` routes in Epic 2.
- **Voice Event Telemetry**: asyncpg's `set_config()` pattern (transaction-scoped, NOT session-scoped) must be used for all RLS context in voice event handlers. See `_bmad-output/implementation-artifacts/1-3-*.md` Discovery #1.
