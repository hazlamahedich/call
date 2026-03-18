# AI Cold Caller SaaS

A production-ready platform for automated cold calling using Next.js, FastAPI, and Turborepo.

## Project Structure

- `apps/web`: Next.js frontend application.
- `apps/api`: FastAPI backend service with SQLModel.
- `packages/types`: Shared TypeScript definitions.
- `packages/constants`: Global constants and configurations.
- `packages/compliance`: Compliance rules and governance logic.
- `tests/`: Playwright E2E and API testing framework.

## Getting Started

### Prerequisites

- Node.js (v20+)
- pnpm (v10+)
- Python (3.12+)
- Docker (for PostgreSQL/VectorDB)

### Local Development

1. **Install dependencies:**
   ```bash
   pnpm install
   ```

2. **Initialize Backend Environment:**
   ```bash
   cd apps/api
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Start Development Servers:**
   ```bash
   pnpm dev
   ```

### Testing

Run the full testing suite:
```bash
pnpm test
```

Run E2E tests only:
```bash
pnpm test:e2e
```

## Architecture Pillars

- **Latency Budget:** <500ms (Stream-First Design)
- **Multi-layer Tenancy:** Agency-First Hierarchy
- **Regulatory Safety:** Real-time Guardrails (TCPA/DNC)
- **Zero-Latency Handoff:** "Master Join" Protocol
