# pgvector Setup Guide for Epic 3

**Status**: Infrastructure Setup
**Owner**: Winston (Architect) + Charlie (Senior Dev)
**Deadline**: Before Story 3.1
**Priority**: HIGH - Blocks Epic 3 RAG implementation

---

## Overview

Epic 3 (Knowledge & Context) requires pgvector for vector similarity search in RAG namespacing. This guide ensures PostgreSQL is properly configured.

---

## Step 1: Verify pgvector Extension

```sql
-- Check if pgvector is installed
SELECT * FROM pg_extension WHERE extname = 'vector';

-- If not installed, install it
CREATE EXTENSION IF NOT EXISTS vector;
```

**Expected Output**:
```
 extname | extowner | extnamespace | extrelocatable | extversion | extconfig | extcondition
---------+----------+--------------+----------------+------------+-----------+--------------
 vector  |      10  |         2200 | f              | 0.5.0      |           |
(1 row)
```

---

## Step 2: Validate Embedding Dimensions

Different AI providers use different embedding dimensions:

| Provider | Model | Dimensions |
|----------|-------|-------------|
| OpenAI | text-embedding-3-small | 1536 |
| OpenAI | text-embedding-3-large | 3072 |
| Anthropic | N/A (uses OpenAI) | varies |

**Recommended**: Use OpenAI `text-embedding-3-small` (1536 dimensions) for cost-efficiency.

---

## Step 3: Create Vector Table Schema

```sql
-- Knowledge embeddings table (Story 3.1)
CREATE TABLE knowledge_embeddings (
    id BIGSERIAL PRIMARY KEY,
    org_id VARCHAR(255) NOT NULL,  -- Tenant isolation
    knowledge_id BIGINT NOT NULL,  -- FK to knowledge_documents
    chunk_text TEXT NOT NULL,      -- Text chunk for context retrieval
    embedding vector(1536),        -- OpenAI text-embedding-3-small
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- RLS Policy
    CONSTRAINT fk_knowledge FOREIGN KEY (knowledge_id) 
        REFERENCES knowledge_documents(id) ON DELETE CASCADE
);

-- Create index for vector similarity search
CREATE INDEX idx_knowledge_embeddings_org_id 
    ON knowledge_embeddings(org_id);

CREATE INDEX idx_knowledge_embeddings_embedding 
    ON knowledge_embeddings 
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);  -- Adjust based on dataset size

-- RLS: Tenant isolation
ALTER TABLE knowledge_embeddings ENABLE ROW LEVEL SECURITY;

CREATE POLICY knowledge_embeddings_tenant_policy 
    ON knowledge_embeddings 
    USING (org_id = current_setting('jwt.org_id', true));
```

---

## Step 4: Vector Similarity Search Query

```python
# Python example for Story 3.1 RAG retrieval

async def find_similar_chunks(
    session: AsyncSession,
    org_id: str,
    query_embedding: list[float],  # From OpenAI embeddings API
    limit: int = 5,
    threshold: float = 0.7,  # Cosine similarity threshold
) -> list[dict]:
    """
    Find similar knowledge chunks using vector similarity search.
    
    Args:
        session: Database session
        org_id: Organization ID for tenant isolation
        query_embedding: Query vector from OpenAI API
        limit: Max number of results
        threshold: Minimum cosine similarity (0-1)
    
    Returns:
        List of similar chunks with similarity scores
    """
    await set_tenant_context(session, org_id)
    
    result = await session.execute(
        text("""
            SELECT 
                chunk_text,
                knowledge_id,
                1 - (embedding <=> :query_vector::vector) as similarity
            FROM knowledge_embeddings
            WHERE org_id = :org_id
              AND 1 - (embedding <=> :query_vector::vector) > :threshold
            ORDER BY embedding <=> :query_vector::vector
            LIMIT :limit
        """),
        {
            "org_id": org_id,
            "query_vector": str(query_embedding),  # Convert to vector string format
            "threshold": threshold,
            "limit": limit,
        }
    )
    
    return [
        {
            "chunk_text": row.chunk_text,
            "knowledge_id": row.knowledge_id,
            "similarity": float(row.similarity),
        }
        for row in result.fetchall()
    ]
```

---

## Step 5: Tenant-Isolated Namespace Pattern

Epic 3 requires tenant-isolated RAG namespaces (each org has their own knowledge base):

```sql
-- Ensure vector searches are tenant-isolated
-- The RLS policy on org_id handles this automatically

-- Example query with explicit tenant check
SELECT 
    chunk_text,
    knowledge_id,
    embedding <=> :query_vector::vector as distance
FROM knowledge_embeddings
WHERE org_id = :org_id  -- RLS enforces this, but explicit is clearer
ORDER BY embedding <=> :query_vector::vector
LIMIT 10;
```

**Key Point**: The `org_id` column is indexed and RLS-protected, ensuring:
- Vector searches never cross tenant boundaries
- Each org's knowledge is isolated
- Performance is optimized with org_id index

---

## Step 6: Configuration Update

Add to `apps/api/config/settings.py`:

```python
class Settings(BaseSettings):
    # ... existing settings ...
    
    # OpenAI Embeddings (for RAG)
    OPENAI_EMBEDDINGS_MODEL: str = "text-embedding-3-small"
    OPENAI_EMBEDDINGS_DIMENSIONS: int = 1536
    
    # Vector similarity thresholds
    RAG_SIMILARITY_THRESHOLD: float = 0.7
    RAG_MAX_RESULTS: int = 5
```

---

## Step 7: Testing pgvector

```python
"""
Test pgvector setup
Story 3.1 Integration Test
"""

import pytest
from sqlalchemy import text

@pytest.mark.asyncio
async def test_pgvector_extension_exists(session: AsyncSession):
    """[3.1-INTEGRATION-001] pgvector extension is installed"""
    result = await session.execute(
        text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
    )
    assert result.scalar() == "vector"

@pytest.mark.asyncio
async def test_vector_similarity_search(session: AsyncSession):
    """[3.1-INTEGRATION-002] Vector similarity search works"""
    # Insert test vectors
    await session.execute(
        text("""
            INSERT INTO knowledge_embeddings (org_id, knowledge_id, chunk_text, embedding)
            VALUES 
                ('test_org', 1, 'hello world', '[0.1, 0.2, 0.3]'::vector),
                ('test_org', 2, 'goodbye world', '[0.9, 0.8, 0.7]'::vector)
        """)
    )
    await session.commit()
    
    # Query for similar vectors
    result = await session.execute(
        text("""
            SELECT chunk_text, embedding <=> '[0.1, 0.2, 0.3]'::vector as distance
            FROM knowledge_embeddings
            WHERE org_id = 'test_org'
            ORDER BY embedding <=> '[0.1, 0.2, 0.3]'::vector
            LIMIT 1
        """)
    )
    row = result.fetchone()
    assert row.chunk_text == "hello world"
    assert row.distance < 0.1  # Should be very similar
```

---

## Verification Checklist

Before starting Story 3.1, verify:

- [ ] pgvector extension is installed (`SELECT extname FROM pg_extension WHERE extname = 'vector'`)
- [ ] Can create vector columns (`vector(1536)`)
- [ ] Can create ivfflat indexes on vector columns
- [ ] Vector similarity search (`<=>` operator) returns results
- [ ] RLS policies work on vector tables (tenant isolation)
- [ ] Performance: Similarity search on 10K vectors < 100ms
- [ ] Python asyncpg can cast list[float] to vector type

---

## Troubleshooting

### Issue: "type vector does not exist"

**Solution**: Install pgvector extension
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Issue: "operator does not exist: vector <=> vector"

**Solution**: The `<=>` operator is provided by pgvector. Reinstall extension:
```sql
DROP EXTENSION IF EXISTS vector;
CREATE EXTENSION vector;
```

### Issue: "could not find extension"

**Solution**: Install pgvector on PostgreSQL server:
```bash
# For PostgreSQL on Ubuntu/Debian
sudo apt-get install postgresql-17-pgvector

# For Neon (cloud PostgreSQL)
# Already installed, just CREATE EXTENSION vector
```

---

## Performance Tuning

For large datasets (>100K vectors), adjust ivfflat index parameters:

```sql
-- Recreate index with optimized lists parameter
-- lists = sqrt(num_vectors) is a good starting point
DROP INDEX idx_knowledge_embeddings_embedding;
CREATE INDEX idx_knowledge_embeddings_embedding 
    ON knowledge_embeddings 
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 1000);  -- Increase for larger datasets
```

---

**Next Steps**: Once pgvector is verified, proceed with Story 3.1 (Knowledge Ingestion).

**Owner**: Winston (Architect)
**Review Date**: 2026-04-04
