"""create knowledge_base and knowledge_chunks tables with pgvector

Revision ID: n9o0p1q2r3s4
Revises: m8n9o0p1q2r3
Create Date: 2026-04-04 22:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "n9o0p1q2r3s4"
down_revision: Union[str, Sequence[str], None] = "m8n9o0p1q2r3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # SECURITY NOTE: This migration uses raw SQL with hardcoded literal values.
    # All values in this migration are constants and safe from SQL injection.
    # DO NOT modify this code to include dynamic values without proper parameterization.

    # Enable pgvector extension
    conn.execute(
        sa.text("""
            CREATE EXTENSION IF NOT EXISTS vector
        """)
    )

    # Create knowledge_bases table
    conn.execute(
        sa.text("""
        CREATE TABLE IF NOT EXISTS knowledge_bases (
            id SERIAL PRIMARY KEY,
            org_id VARCHAR(255) NOT NULL,
            title VARCHAR(200) NOT NULL,
            source_type VARCHAR(10) NOT NULL CHECK (source_type IN ('pdf', 'url', 'text')),
            source_url VARCHAR(2048),
            file_path VARCHAR(512),
            file_storage_url VARCHAR(512),
            content_hash VARCHAR(64),
            chunk_count INTEGER NOT NULL DEFAULT 0,
            status VARCHAR(20) NOT NULL DEFAULT 'processing' CHECK (status IN ('processing', 'ready', 'failed')),
            error_message VARCHAR(1000),
            metadata JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            soft_delete BOOLEAN DEFAULT FALSE NOT NULL
        )
    """)
    )

    # Create indexes for knowledge_bases
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_bases_org_id ON knowledge_bases(org_id)"
        )
    )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_bases_org_status ON knowledge_bases(org_id, status)"
        )
    )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_bases_org_created ON knowledge_bases(org_id, created_at)"
        )
    )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_bases_org_hash ON knowledge_bases(org_id, content_hash)"
        )
    )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_bases_soft_delete ON knowledge_bases(soft_delete)"
        )
    )

    # Create knowledge_chunks table
    conn.execute(
        sa.text("""
        CREATE TABLE IF NOT EXISTS knowledge_chunks (
            id SERIAL PRIMARY KEY,
            org_id VARCHAR(255) NOT NULL,
            knowledge_base_id INTEGER NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            embedding vector(1536),
            embedding_model VARCHAR(100),
            metadata JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            soft_delete BOOLEAN DEFAULT FALSE NOT NULL
        )
    """)
    )

    # Create indexes for knowledge_chunks
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_org_id ON knowledge_chunks(org_id)"
        )
    )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_kb_id ON knowledge_chunks(org_id, knowledge_base_id)"
        )
    )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_soft_delete ON knowledge_chunks(soft_delete)"
        )
    )

    # Create HNSW vector similarity index on embedding column
    # Parameters: m=16 (connections per node), ef_construction=256 (build-time accuracy)
    conn.execute(
        sa.text("""
        CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_embedding_hnsw
        ON knowledge_chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 256)
    """)
    )

    # Enable Row Level Security on both tables
    conn.execute(sa.text("ALTER TABLE knowledge_bases ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE knowledge_chunks ENABLE ROW LEVEL SECURITY"))

    # Create RLS policies for knowledge_bases
    # SELECT policy - tenant isolation
    conn.execute(
        sa.text("""
        CREATE POLICY kb_tenant_isolation_select ON knowledge_bases
        FOR SELECT USING (org_id = current_setting('app.current_org_id', true)::text)
    """)
    )

    # INSERT policy - prevent org_id spoofing
    conn.execute(
        sa.text("""
        CREATE POLICY kb_tenant_insert ON knowledge_bases
        FOR INSERT WITH CHECK (org_id = current_setting('app.current_org_id', true)::text)
    """)
    )

    # UPDATE policy - tenant isolation
    conn.execute(
        sa.text("""
        CREATE POLICY kb_tenant_update ON knowledge_bases
        FOR UPDATE USING (org_id = current_setting('app.current_org_id', true)::text)
    """)
    )

    # DELETE policy - tenant isolation
    conn.execute(
        sa.text("""
        CREATE POLICY kb_tenant_delete ON knowledge_bases
        FOR DELETE USING (org_id = current_setting('app.current_org_id', true)::text)
    """)
    )

    # Platform admin bypass policies
    conn.execute(
        sa.text("""
        CREATE POLICY kb_platform_admin_bypass ON knowledge_bases
        USING (current_setting('app.is_platform_admin', true)::boolean = true)
    """)
    )

    conn.execute(
        sa.text("""
        CREATE POLICY kb_platform_admin_bypass_insert ON knowledge_bases
        FOR INSERT WITH CHECK (current_setting('app.is_platform_admin', true)::boolean = true)
    """)
    )

    # Create RLS policies for knowledge_chunks
    # SELECT policy - tenant isolation
    conn.execute(
        sa.text("""
        CREATE POLICY kc_tenant_isolation_select ON knowledge_chunks
        FOR SELECT USING (org_id = current_setting('app.current_org_id', true)::text)
    """)
    )

    # INSERT policy - prevent org_id spoofing
    conn.execute(
        sa.text("""
        CREATE POLICY kc_tenant_insert ON knowledge_chunks
        FOR INSERT WITH CHECK (org_id = current_setting('app.current_org_id', true)::text)
    """)
    )

    # UPDATE policy - tenant isolation
    conn.execute(
        sa.text("""
        CREATE POLICY kc_tenant_update ON knowledge_chunks
        FOR UPDATE USING (org_id = current_setting('app.current_org_id', true)::text)
    """)
    )

    # DELETE policy - tenant isolation
    conn.execute(
        sa.text("""
        CREATE POLICY kc_tenant_delete ON knowledge_chunks
        FOR DELETE USING (org_id = current_setting('app.current_org_id', true)::text)
    """)
    )

    # Platform admin bypass policies
    conn.execute(
        sa.text("""
        CREATE POLICY kc_platform_admin_bypass ON knowledge_chunks
        USING (current_setting('app.is_platform_admin', true)::boolean = true)
    """)
    )

    conn.execute(
        sa.text("""
        CREATE POLICY kc_platform_admin_bypass_insert ON knowledge_chunks
        FOR INSERT WITH CHECK (current_setting('app.is_platform_admin', true)::boolean = true)
    """)
    )

    # Create triggers for automatic org_id and timestamp management
    # Trigger function to set org_id from context
    conn.execute(
        sa.text("""
        CREATE OR REPLACE FUNCTION set_org_id_from_context()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.org_id := current_setting('app.current_org_id', true)::text;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    )

    # Trigger function to update updated_at timestamp
    conn.execute(
        sa.text("""
        CREATE OR REPLACE FUNCTION update_timestamp()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at := CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    )

    # Apply triggers to knowledge_bases
    conn.execute(
        sa.text("""
        CREATE TRIGGER kb_set_org_id
        BEFORE INSERT ON knowledge_bases
        FOR EACH ROW
        WHEN (NEW.org_id IS NULL)
        EXECUTE FUNCTION set_org_id_from_context()
    """)
    )

    conn.execute(
        sa.text("""
        CREATE TRIGGER kb_update_timestamp
        BEFORE UPDATE ON knowledge_bases
        FOR EACH ROW
        EXECUTE FUNCTION update_timestamp()
    """)
    )

    # Apply triggers to knowledge_chunks
    conn.execute(
        sa.text("""
        CREATE TRIGGER kc_set_org_id
        BEFORE INSERT ON knowledge_chunks
        FOR EACH ROW
        WHEN (NEW.org_id IS NULL)
        EXECUTE FUNCTION set_org_id_from_context()
    """)
    )


def downgrade() -> None:
    conn = op.get_bind()

    # Drop triggers
    conn.execute(sa.text("DROP TRIGGER IF EXISTS kc_set_org_id ON knowledge_chunks"))
    conn.execute(sa.text("DROP TRIGGER IF EXISTS kb_update_timestamp ON knowledge_bases"))
    conn.execute(sa.text("DROP TRIGGER IF EXISTS kb_set_org_id ON knowledge_bases"))

    # Drop trigger functions
    conn.execute(sa.text("DROP FUNCTION IF EXISTS update_timestamp()"))
    conn.execute(sa.text("DROP FUNCTION IF EXISTS set_org_id_from_context()"))

    # Drop RLS policies for knowledge_chunks
    conn.execute(sa.text("DROP POLICY IF EXISTS kc_platform_admin_bypass_insert ON knowledge_chunks"))
    conn.execute(sa.text("DROP POLICY IF EXISTS kc_platform_admin_bypass ON knowledge_chunks"))
    conn.execute(sa.text("DROP POLICY IF EXISTS kc_tenant_delete ON knowledge_chunks"))
    conn.execute(sa.text("DROP POLICY IF EXISTS kc_tenant_update ON knowledge_chunks"))
    conn.execute(sa.text("DROP POLICY IF EXISTS kc_tenant_insert ON knowledge_chunks"))
    conn.execute(sa.text("DROP POLICY IF EXISTS kc_tenant_isolation_select ON knowledge_chunks"))

    # Drop RLS policies for knowledge_bases
    conn.execute(sa.text("DROP POLICY IF EXISTS kb_platform_admin_bypass_insert ON knowledge_bases"))
    conn.execute(sa.text("DROP POLICY IF EXISTS kb_platform_admin_bypass ON knowledge_bases"))
    conn.execute(sa.text("DROP POLICY IF EXISTS kb_tenant_delete ON knowledge_bases"))
    conn.execute(sa.text("DROP POLICY IF EXISTS kb_tenant_update ON knowledge_bases"))
    conn.execute(sa.text("DROP POLICY IF EXISTS kb_tenant_insert ON knowledge_bases"))
    conn.execute(sa.text("DROP POLICY IF EXISTS kb_tenant_isolation_select ON knowledge_bases"))

    # Disable RLS
    conn.execute(sa.text("ALTER TABLE knowledge_chunks DISABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE knowledge_bases DISABLE ROW LEVEL SECURITY"))

    # Drop indexes
    conn.execute(sa.text("DROP INDEX IF EXISTS idx_knowledge_chunks_embedding_hnsw"))
    conn.execute(sa.text("DROP INDEX IF EXISTS idx_knowledge_chunks_soft_delete"))
    conn.execute(sa.text("DROP INDEX IF EXISTS idx_knowledge_chunks_kb_id"))
    conn.execute(sa.text("DROP INDEX IF EXISTS idx_knowledge_chunks_org_id"))
    conn.execute(sa.text("DROP INDEX IF EXISTS idx_knowledge_bases_soft_delete"))
    conn.execute(sa.text("DROP INDEX IF EXISTS idx_knowledge_bases_org_hash"))
    conn.execute(sa.text("DROP INDEX IF EXISTS idx_knowledge_bases_org_created"))
    conn.execute(sa.text("DROP INDEX IF EXISTS idx_knowledge_bases_org_status"))
    conn.execute(sa.text("DROP INDEX IF EXISTS idx_knowledge_bases_org_id"))

    # Drop tables
    conn.execute(sa.text("DROP TABLE IF EXISTS knowledge_chunks"))
    conn.execute(sa.text("DROP TABLE IF EXISTS knowledge_bases"))

    # Note: pgvector extension is not dropped to avoid affecting other potential users
