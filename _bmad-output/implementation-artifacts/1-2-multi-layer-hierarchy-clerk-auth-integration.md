# Story 1.2: Multi-layer Hierarchy & Clerk Auth Integration

Status: ready-for-dev

## Story

As a Platform Provider,
I want to manage Agency and Client sub-accounts using Clerk Organizations,
so that I can maintain a strict three-tier business hierarchy.

## Acceptance Criteria

1. **Organization Creation**: Given a user is logged into the management portal, when they create a new Agency organization, then the organization is created in Clerk with the correct metadata structure. [Source: epics.md#Story 1.2]
2. **Client Sub-account Assignment**: Given an Agency organization exists, when an admin assigns Client sub-accounts, then they can be managed within the Clerk dashboard/API. [Source: epics.md#Story 1.2]
3. **Permission Scoping**: Given users with different roles (Admin, Member), when they access the system, then their permissions are correctly scoped to their specific Organization level. [Source: epics.md#Story 1.2]
4. **API Middleware Validation**: Given a request to `apps/api`, when authentication middleware processes it, then the `org_id` is validated for every request. [Source: epics.md#Story 1.2]
5. **Frontend Auth Integration**: Given the `apps/web` frontend, when Clerk is integrated, then authentication state and organization context are available throughout the app. [Source: architecture.md#Step 4]

## Tasks / Subtasks

- [ ] Install and configure Clerk SDK (AC: 1, 5)
  - [ ] Add `@clerk/nextjs` to `apps/web/package.json`
  - [ ] Add `clerk-backend` to `apps/api/requirements.txt`
  - [ ] Configure Clerk provider in `apps/web/src/app/layout.tsx`
  - [ ] Set up environment variables (`NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`)
- [ ] Implement Agency organization creation flow (AC: 1)
  - [ ] Create organization creation API route using Server Actions
  - [ ] Add organization metadata schema (type: "agency", plan, settings)
  - [ ] Create UI component for organization creation form
- [ ] Implement Client sub-account management (AC: 2)
  - [ ] Design Client metadata structure within Agency organization
  - [ ] Create Client sub-account creation/assignment API endpoints
  - [ ] Build Client management UI in dashboard
- [ ] Implement role-based permission scoping (AC: 3)
  - [ ] Configure Clerk roles (org:admin, org:member)
  - [ ] Create permission helper functions for frontend
  - [ ] Implement role-based access control middleware
- [ ] Build API authentication middleware (AC: 4)
  - [ ] Create `apps/api/middleware/auth.py` for JWT validation
  - [ ] Extract and validate `org_id` from Clerk session token
  - [ ] Add organization context to request state
- [ ] Create shared auth types (AC: 4, 5)
  - [ ] Define auth-related types in `packages/types/auth.ts`
  - [ ] Create organization/user interface definitions
  - [ ] Add error codes for auth failures in `packages/constants`

## Dev Notes

### Architecture Compliance

- **Authentication Provider**: Clerk with Organizations feature enabled. [Source: architecture.md#Step 4]
- **Hierarchy Mapping**: Clerk `Organizations` → `Agencies`; `OrganizationMembers` → `Client Sub-accounts`. [Source: architecture.md#Step 4]
- **Naming Convention**: Backend uses `snake_case`; Frontend uses `camelCase`; use `AliasGenerator` for conversion. [Source: architecture.md#Step 5]
- **Server Actions**: Use `"use server"` directive for data mutations in Next.js 15. [Source: project-context.md]

### Clerk-Specific Implementation

- **Organization Metadata**: Use Clerk's `publicMetadata` and `privateMetadata` for storing agency/client configuration
- **JWT Template**: Configure Clerk JWT template to include `org_id`, `org_role`, and custom claims
- **Webhook Events**: Subscribe to `organization.created`, `organizationMembership.created` for sync
- **Multi-tenant Context**: Pass `org_id` in all API requests via Authorization header

### Previous Story Learnings (1.1)

- Monorepo structure is established with Turborepo
- `apps/web` uses Next.js 15 App Router with Vanilla CSS
- `apps/api` uses FastAPI with SQLModel
- Shared packages exist: `@call/types`, `@call/constants`, `@call/compliance`
- Testing: Playwright (E2E), Pytest (backend)
- All tests verified passing via `turbo test`

### Testing Requirements

- **Unit Tests**: Auth middleware tests in `apps/api/tests/test_auth.py`
- **E2E Tests**: Login flow, organization creation, role-based access in `tests/e2e/auth.spec.ts`
- **Mocking**: Mock Clerk SDK calls during testing to ensure deterministic results
- **Coverage Target**: >80% for auth-related code

### Project Structure Notes

```
apps/web/
├── src/
│   ├── app/
│   │   ├── (auth)/
│   │   │   ├── sign-in/[[...sign-in]]/
│   │   │   └── sign-up/[[...sign-up]]/
│   │   ├── (dashboard)/
│   │   │   └── dashboard/
│   │   │       ├── organizations/
│   │   │       └── clients/
│   │   └── layout.tsx  # ClerkProvider wrapper
│   ├── lib/
│   │   └── clerk.ts    # Clerk helpers
│   └── middleware.ts   # Clerk middleware

apps/api/
├── middleware/
│   └── auth.py         # JWT validation, org_id extraction
├── routers/
│   └── auth.py         # Auth-related endpoints
└── models/
    └── organization.py # SQLModel for org sync

packages/types/
├── auth.ts             # Auth-related TypeScript interfaces
└── organization.ts     # Organization interfaces
```

### References

- [EPIC: epics.md#Epic 1: Multi-tenant Foundation & Identity]
- [Auth Architecture: architecture.md#Step 4: Authentication & Security]
- [Naming Rules: architecture.md#Step 5: Implementation Patterns & Consistency Rules]
- [Project Context: project-context.md#Database & Security]
- [Previous Story: 1-1-hybrid-monorepo-core-infrastructure-scaffolding.md]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
