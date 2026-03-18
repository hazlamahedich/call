# Story 1.1: Hybrid Monorepo & Core Infrastructure Scaffolding

Status: done

<!-- Note: Validation performed by QA Agent Quinn on 2026-03-17. -->

## Story

As a Developer,
I want a unified monorepo structure with Turborepo, FastAPI, and Next.js,
so that I can build the frontend and backend in a synchronized workspace.

## Acceptance Criteria

1. **Initialization**: Running `npx create-turbo@latest ./` initializes the monorepo correctly. [Source: architecture.md#Step 3]
2. **Frontend Entry**: `apps/web` contains a Next.js 15 application using the App Router. [Source: project-context.md#Monorepo Layout]
3. **Backend Entry**: `apps/api` contains a FastAPI service. [Source: project-context.md#Monorepo Layout]
4. **Pipeline Definition**: `turbo.json` defines pipelines for `build`, `dev`, and `typecheck` across all apps and packages. [Source: epics.md#Story 1.1]
5. **Shared Types**: `packages/types` is established and accessible by both `web` and `api` projects for type synchronization. [Source: architecture.md#Step 5]

## Tasks / Subtasks

- [x] Initialize Turborepo core (AC: 1)
  - [x] Run `npx create-turbo@latest ./` in the project root.
- [x] Scaffold `apps/web` (AC: 2)
  - [x] Ensure Next.js 15 is configured with App Router and Vanilla CSS support.
- [x] Scaffold `apps/api` (AC: 3)
  - [x] Initialize FastAPI project structure with `snake_case` naming and `SQLModel` foundations.
- [x] Configure Turborepo pipelines (AC: 4)
  - [x] Update `turbo.json` to include `build`, `dev`, and `typecheck`.
- [x] Establish shared packages (AC: 5)
  - [x] Create `packages/types`, `packages/constants`, and `packages/compliance`.

## Dev Notes

- **Architecture Compliance**:
  - Use **Turborepo** for monorepo management and **pnpm** (10.26.1) as the package manager. [Source: project-context.md]
  - Backend must use `snake_case` and `SQLModel`; Frontend must use `camelCase` and Geist fonts. [Source: architecture.md#Step 5]
  - Frontend strictly uses **Next.js 15 App Router** and **Vanilla CSS**. [Source: project-context.md]
- **Testing Standards**:
  - `apps/web` uses **Playwright**; `apps/api` uses **Pytest**. [Source: project-context.md]
  - Mock external AI streams (Vapi, Cartesia) during E2E/Unit testing. [Source: project-context.md]

### Project Structure Notes

- `apps/web`: Next.js 15 (Dashboard/Cockpit).
- `apps/api`: FastAPI (Voice/Logic).
- `packages/compliance`: DNC/TCPA logic.
- `packages/types`: Shared TypeScript interfaces.
- `packages/constants`: Shared error codes and registry.

### References

- [EPIC Analysis: epics.md#Epic 1: Multi-tenant Foundation & Identity]
- [Architecture Pillars: architecture.md#Core Architectural Pillars]
- [Naming Rules: architecture.md#Step 5: Implementation Patterns & Consistency Rules]
- [UX Specifications: ux-design-specification.md#Step 6: Design System Foundation]

## QA Results

### Audit Summary

- **AC Alignment**: AC 1–5 are clearly defined and traceable to `architecture.md` and `project-context.md`.
- **Technical Compliance**: Correct versions specified (Next.js 15, pnpm 10.26.1). Architectural pillars (FastAPI, SQLModel, Turborepo) are properly integrated into tasks.
- **Naming Conventions**: `snake_case` (backend) and `camelCase` (frontend) specified in dev notes.
- **Completeness**: Tasks cover all initialization steps for the monorepo and core apps.

### QA Status

- [x] Acceptance Criteria clear and measurable
- [x] Tasks cover all ACs
- [x] Technical constraints documented
- [x] References provided

**Verdict**: ✅ **Passed** - Implementation verified by Dev Agent.

## Dev Agent Record

### Agent Model Used

Antigravity (Gemini 2.0 Pro)

### Debug Log References

- [Task Artifact](file:///Users/sherwingorechomante/.gemini/antigravity/brain/06e70781-43c4-45be-875c-dfc61cb30e28/task.md)
- [Implementation Plan](file:///Users/sherwingorechomante/.gemini/antigravity/brain/06e70781-43c4-45be-875c-dfc61cb30e28/implementation_plan.md)
- [Walkthrough](file:///Users/sherwingorechomante/.gemini/antigravity/brain/06e70781-43c4-45be-875c-dfc61cb30e28/walkthrough.md)

### Completion Notes List

- Successfully scaffolded Turborepo with pnpm workspaces.
- Initialized Next.js 15 `apps/web` with App Router and Vanilla CSS.
- Initialized FastAPI `apps/api` with SQLModel, settings, and modular routing.
- Created shared packages `@call/types`, `@call/constants`, and `@call/compliance`.
- Verified build and typecheck pipelines via `turbo build typecheck`.
- **Verified all automated tests (Unit & E2E) are passing via `turbo test`.**
  - Backend: `pytest` with `PYTHONPATH` and `TestClient` initialized.
  - E2E: `Playwright` sanity tests passing in Chromium.

### File List

- `apps/web/package.json`
- `apps/api/main.py`
- `apps/api/config/settings.py`
- `apps/api/database/base.py`
- `apps/api/tests/test_health.py`
- `packages/types/package.json`
- `packages/constants/package.json`
- `packages/compliance/package.json`
- `tests/package.json`
- `tests/playwright.config.ts`
- `tests/e2e/sanity.spec.ts`
- `turbo.json`
- `pnpm-workspace.yaml`

