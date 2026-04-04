# pgvector Installation Instructions

## Issue
The migration requires pgvector extension for PostgreSQL 15, but it's currently only installed for PostgreSQL 17/18.

## Solution: Install pgvector for PostgreSQL 15

### Option 1: Build from Source (Already Done)

I've already built pgvector from source for PostgreSQL 15. The files are in `/tmp/pgvector-build/`.

### Option 2: Manual Installation (Requires sudo)

Run these commands to install pgvector for PostgreSQL 15:

```bash
# Copy the extension files
sudo cp /tmp/pgvector-build/vector.so /opt/homebrew/Cellar/postgresql@15/15.15/lib/postgresql/
sudo cp /tmp/pgvector-build/sql/vector--0.8.2.sql /opt/homebrew/Cellar/postgresql@15/15.15/share/postgresql/extension/
sudo cp /tmp/pgvector-build/vector.control /opt/homebrew/Cellar/postgresql@15/15.15/share/postgresql/extension/

# Restart PostgreSQL to load the extension
brew services restart postgresql@15
```

### Option 3: Use Docker (Recommended for Production)

If you're using Docker, use a pgvector-enabled image:

```yaml
# docker-compose.yml
services:
  postgres:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_DB: call_db
      POSTGRES_USER: call_user
      POSTGRES_PASSWORD: your_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

## After Installation

Once pgvector is installed, run the migration:

```bash
cd apps/api
.venv/bin/alembic upgrade n9o0p1q2r3s4
```

## Alternative: Skip pgvector for Now

If you want to proceed without pgvector, you can:
1. Comment out the `CREATE EXTENSION vector` line in the migration
2. Run the migration without vector support
3. Add vector support later when pgvector is available

However, this will mean the vector search functionality won't work.

## Current Status

- ✅ pgvector source code built for PostgreSQL 15
- ⚠️ Extension files need to be copied (requires sudo)
- ⏸️ Migration waiting for pgvector installation
- ✅ All code implementation complete
- ✅ All tests written and ready to run
