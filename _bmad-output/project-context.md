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

### Monorepo Layout
- `apps/web`: Next.js frontend.
- `apps/api`: FastAPI backend.
- `packages/types`: Shared TypeScript interfaces.
- `packages/compliance`: DNC/TCPA logic.
- `packages/constants`: Shared error codes and registry.
