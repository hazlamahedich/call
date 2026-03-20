# Story 1.2: Multi-layer Hierarchy & Clerk Auth Integration

Status: ready-for-dev

## Story

As a Platform Provider,
I want to manage Agency and Client sub-accounts using Clerk Organizations,
so that I can maintain a strict three-tier business hierarchy.

## Acceptance Criteria

1. **Organization Creation**: Given a user is logged into the management portal, when they create a new Agency organization via our UI, then the organization is created in Clerk with metadata: `{type: "agency", plan: string, settings: object}`. [Source: epics.md#Story 1.2]

2. **Client Sub-account Assignment**: Given an Agency organization exists, when an admin creates a Client via our UI, then the Client is stored as `publicMetadata` on the Agency organization with structure: `{clients: [{id: string, name: string, settings: object}]}`. [Source: epics.md#Story 1.2]

3. **Permission Scoping**: Given users with different roles (org:admin, org:member), when they access the system, then:
   - org:admin can CRUD organizations, manage members, view all client data
   - org:member can view organization data, manage assigned clients only
   [Source: epics.md#Story 1.2]

4. **API Middleware Validation**: Given a request to `apps/api`, when authentication middleware processes it, then:
   - JWT is validated via Clerk's JWKS endpoint
   - `org_id` is extracted and attached to `request.state.org_id`
   - Invalid/missing tokens return 401 with error code `AUTH_INVALID_TOKEN`
   - Expired tokens return 401 with error code `AUTH_TOKEN_EXPIRED`
   [Source: epics.md#Story 1.2]

5. **Frontend Auth Integration**: Given the `apps/web` frontend, when Clerk is integrated, then:
   - `useAuth()` and `useOrganization()` hooks are available app-wide
   - Protected routes redirect to `/sign-in` when unauthenticated
   - Organization context persists across navigation
   [Source: architecture.md#Step 4]

6. **Error Handling**: Given auth-related failures, when errors occur, then:
   - Clerk service unavailable → Display "Authentication temporarily unavailable" with retry button
   - Invalid session → Redirect to sign-in with toast notification "Session expired"
   - Unauthorized org access → Return 403 with user-friendly error message

## Tasks / Subtasks

- [ ] Install and configure Clerk SDK (AC: 1, 5)
  - [ ] Add `@clerk/nextjs` to `apps/web/package.json`
  - [ ] Add `pyjwt` and `svix` to `apps/api/requirements.txt`
  - [ ] Configure ClerkProvider in `apps/web/src/app/layout.tsx`
  - [ ] Create `apps/web/.env.local` with `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`
  - [ ] Create `apps/api/.env` with `CLERK_SECRET_KEY`, `CLERK_JWKS_URL`

- [ ] Configure Clerk JWT templates (AC: 4)
  - [ ] Create JWT template in Clerk dashboard with `org_id`, `org_role` claims
  - [ ] Test JWT token contains required claims via Clerk's token preview
  - [ ] Document claim structure in `packages/types/auth.ts`

- [ ] Implement Agency organization creation flow (AC: 1)
  - [ ] Create Server Action in `apps/web/src/actions/organization.ts`
  - [ ] Add organization metadata schema: `{type: "agency", plan: string, settings: object}`
  - [ ] Create UI component for organization creation form at `/dashboard/organizations/new`

- [ ] Implement Client sub-account management (AC: 2)
  - [ ] Design Client metadata structure within Agency `publicMetadata.clients[]`
  - [ ] Create Server Actions for Client CRUD in `apps/web/src/actions/client.ts`
  - [ ] Build Client management UI in `/dashboard/clients`

- [ ] Implement role-based permission scoping (AC: 3)
  - [ ] Configure Clerk roles: `org:admin`, `org:member`
  - [ ] Create permission helper functions in `apps/web/src/lib/permissions.ts`
  - [ ] Implement role-based UI conditional rendering

- [ ] Build API authentication middleware (AC: 4)
  - [ ] Create `apps/api/middleware/auth.py` for JWT validation via JWKS
  - [ ] Extract and validate `org_id` from Clerk session token
  - [ ] Add `org_id` to `request.state` for downstream access
  - [ ] Return appropriate error codes: `AUTH_INVALID_TOKEN`, `AUTH_TOKEN_EXPIRED`

- [ ] Create organization context dependency (AC: 4)
  - [ ] Create `apps/api/dependencies/org_context.py`
  - [ ] Implement `get_current_org_id()` FastAPI dependency
  - [ ] Implement `get_current_user()` FastAPI dependency

- [ ] Implement webhook receiver for Clerk events (AC: 1, 2)
  - [ ] Create `apps/api/routers/webhooks.py` with Svix signature verification
  - [ ] Handle `organization.created` event to sync to local DB
  - [ ] Handle `organizationMembership.created` event for member sync
  - [ ] Add `CLERK_WEBHOOK_SECRET` to environment configuration

- [ ] Create shared auth types (AC: 4, 5)
  - [ ] Define `ClerkJWTClaims`, `Organization`, `User` in `packages/types/auth.ts`
  - [ ] Define `Client` interface in `packages/types/organization.ts`
  - [ ] Add error codes: `AUTH_INVALID_TOKEN`, `AUTH_TOKEN_EXPIRED`, `AUTH_UNAUTHORIZED` in `packages/constants`

- [ ] Write auth middleware unit tests (AC: 4)
  - [ ] Test valid JWT extraction and `org_id` attachment
  - [ ] Test expired token handling (401 + `AUTH_TOKEN_EXPIRED`)
  - [ ] Test malformed token handling (401 + `AUTH_INVALID_TOKEN`)
  - [ ] Test missing Authorization header (401 + `AUTH_INVALID_TOKEN`)
  - [ ] Use pytest with `unittest.mock` for Clerk JWKS calls

- [ ] Write E2E authentication flow tests (AC: 5)
  - [ ] Test sign-in redirects to protected content
  - [ ] Test organization creation creates Clerk org with correct metadata
  - [ ] Test role-based UI visibility (admin sees member management, member doesn't)
  - [ ] Test session persistence across page navigation
  - [ ] Use Playwright with `@clerk/testing` test fixtures

- [ ] Write webhook integration tests (AC: 1, 2)
  - [ ] Test `organization.created` webhook syncs to local DB
  - [ ] Test invalid webhook signature returns 401
  - [ ] Test idempotent webhook handling (same event processed twice)

## Dev Notes

### Architecture Compliance

- **Authentication Provider**: Clerk with Organizations feature enabled. [Source: architecture.md#Step 4]
- **Hierarchy Mapping**: Clerk `Organizations` → `Agencies`; Clients stored as `publicMetadata` on Agency. [Source: architecture.md#Step 4]
- **Naming Convention**: Backend uses `snake_case`; Frontend uses `camelCase`; use `AliasGenerator` for conversion. [Source: architecture.md#Step 5]
- **Server Actions**: Use `"use server"` directive for data mutations in Next.js 15. [Source: project-context.md]

### Client Data Model (Decision: Clients as Metadata)

**Rationale:**
- Clerk's Organizations feature has limits on nested hierarchies
- Clients are sub-entities of Agencies, not independent organizations
- Simpler permission model - Client access controlled by Agency admins

**Client Storage Pattern:**
```typescript
// Agency organization's publicMetadata
{
  type: "agency",
  plan: "pro" | "enterprise",
  clients: [
    {
      id: "uuid",
      name: "Client Corp",
      createdAt: "2026-03-18T...",
      settings: {
        branding: { primaryColor: "#10B981", logo: "url" },
        features: { aiScripts: true, crmIntegration: false }
      }
    }
  ]
}
```

### Edge Case Handling

- **Organization Deletion**: Soft delete only - mark `deletedAt` timestamp in metadata
- **User Multi-Org Membership**: Allowed. User can belong to multiple Agencies with independent roles
- **Client Isolation**: Users with access to Client A cannot see Client B data (enforced in API layer)

### Clerk-Specific Implementation

- **Organization Metadata**: Use Clerk's `publicMetadata` for agency/client configuration (readable by frontend)
- **JWT Template**: Configure Clerk JWT template to include `org_id`, `org_role`, and custom claims
- **Webhook Events**: Subscribe to `organization.created`, `organizationMembership.created` for sync
- **Multi-tenant Context**: Pass `org_id` in all API requests via Authorization header (Bearer token)

### Environment Variables

```bash
# apps/web/.env.local
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...

# apps/api/.env
CLERK_SECRET_KEY=sk_test_...
CLERK_JWKS_URL=https://api.clerk.dev/v1/jwks
CLERK_WEBHOOK_SECRET=whsec_...
```

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
- **Webhook Tests**: Integration tests in `apps/api/tests/test_webhooks.py`
- **Mocking**: Use `unittest.mock` for Python, `jest.mock` for frontend Clerk SDK calls
- **Coverage Target**: >80% for auth-related code

### Project Structure Notes

```
apps/web/
├── src/
│   ├── actions/
│   │   ├── organization.ts    # Server Actions for org CRUD
│   │   └── client.ts          # Server Actions for client CRUD
│   ├── app/
│   │   ├── (auth)/
│   │   │   ├── sign-in/[[...sign-in]]/
│   │   │   └── sign-up/[[...sign-up]]/
│   │   ├── (dashboard)/
│   │   │   └── dashboard/
│   │   │       ├── organizations/
│   │   │       │   └── new/
│   │   │       └── clients/
│   │   └── layout.tsx         # ClerkProvider wrapper
│   ├── lib/
│   │   ├── clerk.ts           # Clerk helpers
│   │   └── permissions.ts     # Role-based permission helpers
│   └── middleware.ts          # Clerk middleware

apps/api/
├── dependencies/
│   └── org_context.py         # FastAPI dependencies for org/user context
├── middleware/
│   └── auth.py                # JWT validation, org_id extraction
├── routers/
│   ├── auth.py                # Auth-related endpoints
│   └── webhooks.py            # Clerk webhook receiver
└── models/
    └── organization.py        # SQLModel for org sync

packages/types/
├── auth.ts                    # Auth-related TypeScript interfaces
└── organization.ts            # Organization/Client interfaces

packages/constants/
└── errors.ts                  # Error codes including auth errors
```

### References

- [EPIC: epics.md#Epic 1: Multi-tenant Foundation & Identity]
- [Auth Architecture: architecture.md#Step 4: Authentication & Security]
- [Naming Rules: architecture.md#Step 5: Implementation Patterns & Consistency Rules]
- [Project Context: project-context.md#Database & Security]
- [Previous Story: 1-1-hybrid-monorepo-core-infrastructure-scaffolding.md]
- [Clerk Docs: https://clerk.com/docs/backend-requests/handling/manual-jwt]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

### Change Log

- **2026-03-20**: Story refined via Party Mode review with Winston (Architect), John (PM), Quinn (QA), Mary (Analyst), Amelia (Dev)
  - Added AC-6 for error handling
  - Refined AC-2 to specify Client storage as metadata (not separate orgs)
  - Added 4 new tasks: JWT templates, webhook receiver, org context dependency, explicit test tasks
  - Corrected `clerk-backend` → `pyjwt` + `svix`
  - Added Client data model design and edge case handling
  - Added explicit environment variable locations
  - Added test subtasks with mocking strategy
