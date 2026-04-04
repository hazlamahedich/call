---
project_name: 'call'
user_name: 'team mantis a'
date: '2026-03-17'
sections_completed: ['technology_stack', 'language_rules', 'testing', 'security']
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

### Canonical Implementation Patterns

#### Server Action Authentication Pattern (Frontend)

All Server Actions MUST follow this canonical pattern established in `apps/web/src/actions/branding.ts`:

```typescript
"use server";

import { auth } from "@clerk/nextjs/server";

export async function myAction(data: { orgId: string }) {
  const { getToken } = await auth();
  const token = await getToken();
  if (!token) return { error: "Not authenticated" };

  const response = await fetch(`${API_URL}/endpoint`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  // ... handle response
}
```

**DO NOT** use the legacy pattern from early Story 1.2 client.ts that lacks auth headers.

#### SQLModel Construction Pattern (Backend)

All SQLModel instances with `table=True` MUST be constructed using `model_validate()` with camelCase aliases:

```python
from models.tenant import TenantModel

# ✅ CORRECT - Use model_validate with camelCase keys
record = MyModel.model_validate({
    "resourceType": "call",
    "resourceId": "123",
    "action": "initiated"
})

# ❌ WRONG - Positional kwargs are silently ignored in table=True models
record = MyModel(
    resource_type="call",
    resource_id="123",
    action="initiated"
)
```

**Rationale**: SQLModel v0.0.x has a known bug where `table=True` constructors silently ignore positional kwargs. The AliasGenerator requires camelCase keys.

#### Provider Abstraction Pattern

All external provider integrations (TTS, LLM, Transcription, etc.) MUST follow the TTSOrchestrator pattern:

1. **Abstract Base Class**: Define interface with abstract methods
2. **Concrete Implementations**: One class per provider (OpenAI, Anthropic, ElevenLabs, etc.)
3. **Orchestrator**: Manages provider selection, fallback, and health tracking
4. **Circuit Breaker**: Automatic failover when provider degrades
5. **Session State**: TTL-based state management (consider Redis for horizontal scaling)

Example structure:
```python
from abc import ABC, abstractmethod

class LLMProviderBase(ABC):
    @abstractmethod
    async def generate(self, prompt: str) -> str:
        pass

class OpenAIProvider(LLMProviderBase):
    async def generate(self, prompt: str) -> str:
        # OpenAI-specific implementation
        pass

class LLMOrchestrator:
    def __init__(self, providers: dict[str, LLMProviderBase]):
        self._providers = providers
        self._fallback_order = list(providers.keys())

    async def generate_with_fallback(self, prompt: str) -> str:
        # Try primary, fallback to next on failure
        pass
```

#### Visual Component Animation Pattern

All visual feedback components MUST use CSS-only animations by default. JavaScript animations require explicit justification.

**CSS-only example** (preferred):
```css
@keyframes pulse {
  0%, 100% { opacity: 0.8; }
  50% { opacity: 1; }
}

.visual-indicator {
  animation: pulse 2s infinite;
}

@media (prefers-reduced-motion: reduce) {
  .visual-indicator {
    animation: none;
  }
}
```

**Benefits**: 60fps, GPU-accelerated, zero JavaScript overhead, WCAG AAA compliant.

#### Test Quality Standards

All test suites MUST follow these standards:

1. **BDD Naming**: Given/When/Then structure in test names
   ```python
   async def test_3_1_001_given_valid_org_when_ingesting_knowledge_then_succeeds():
   ```

2. **Traceability IDs**: Format `[X.X-UNIT-XXX]` or `[X.X-E2E-XXX]`
   ```python
   # [3.1-UNIT-001] Knowledge ingestion creates vector embeddings
   ```

3. **Factory Functions**: Use data factories, not hardcoded values
   ```python
   def create_test_org(org_id: str = "test_org") -> Agency:
       return Agency.model_validate({"orgId": org_id, "name": "Test"})
   ```

4. **No Hard Waits**: Use fake timers or await conditions
   ```python
   # ❌ WRONG
   await asyncio.sleep(5)

   # ✅ CORRECT
   await asyncio.wait_for(condition.wait(), timeout=5.0)
   ```

5. **Cleanup Hooks**: Always cleanup resources
   ```python
   @pytest.fixture(autouse=True)
   async def cleanup():
       yield
       reset_orchestrator()  # Reset singletons
   ```

### Monorepo Layout
- `apps/web`: Next.js frontend.
- `apps/api`: FastAPI backend.
- `packages/types`: Shared TypeScript interfaces.
- `packages/compliance`: DNC/TCPA logic.
- `packages/constants`: Shared error codes and registry.
