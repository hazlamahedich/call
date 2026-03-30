"""add agents and extend scripts

Revision ID: f1g2h3i4j5k6
Revises: d4e5f6g7h8i9
Create Date: 2026-03-30 12:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f1g2h3i4j5k6"
down_revision: Union[str, Sequence[str], None] = "d4e5f6g7h8i9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(
        sa.text("""
        CREATE TABLE IF NOT EXISTS agents (
            id SERIAL PRIMARY KEY,
            org_id TEXT NOT NULL,
            name VARCHAR(255) NOT NULL DEFAULT 'My First Agent',
            voice_id VARCHAR(100) NOT NULL DEFAULT '',
            business_goal VARCHAR(255) NOT NULL DEFAULT '',
            safety_level VARCHAR(50) NOT NULL DEFAULT 'strict',
            integration_type VARCHAR(100),
            onboarding_complete BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            soft_delete BOOLEAN DEFAULT FALSE
        )
    """)
    )
    conn.execute(
        sa.text("CREATE INDEX IF NOT EXISTS idx_agents_org_id ON agents(org_id)")
    )
    conn.execute(sa.text("ALTER TABLE agents ENABLE ROW LEVEL SECURITY"))
    conn.execute(
        sa.text("""
        CREATE POLICY tenant_isolation_agents ON agents
        USING (org_id = current_setting('app.current_org_id', true)::text)
    """)
    )
    conn.execute(
        sa.text("""
        CREATE POLICY tenant_insert_agents ON agents
        FOR INSERT WITH CHECK (org_id = current_setting('app.current_org_id', true)::text)
    """)
    )
    conn.execute(
        sa.text("""
        CREATE POLICY platform_admin_bypass_agents ON agents
        USING (current_setting('app.is_platform_admin', true)::boolean = true)
    """)
    )
    conn.execute(
        sa.text("""
        CREATE POLICY platform_admin_bypass_insert_agents ON agents
        FOR INSERT WITH CHECK (current_setting('app.is_platform_admin', true)::boolean = true)
    """)
    )

    conn.execute(
        sa.text(
            "ALTER TABLE scripts ADD COLUMN IF NOT EXISTS agent_id INTEGER REFERENCES agents(id)"
        )
    )
    conn.execute(
        sa.text(
            "ALTER TABLE scripts ADD COLUMN IF NOT EXISTS name VARCHAR(255) NOT NULL DEFAULT 'Initial Script'"
        )
    )
    conn.execute(
        sa.text(
            "ALTER TABLE scripts ADD COLUMN IF NOT EXISTS content TEXT NOT NULL DEFAULT ''"
        )
    )
    conn.execute(
        sa.text(
            "ALTER TABLE scripts ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1"
        )
    )
    conn.execute(
        sa.text(
            "ALTER TABLE scripts ADD COLUMN IF NOT EXISTS script_context TEXT NOT NULL DEFAULT ''"
        )
    )


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text("ALTER TABLE scripts DROP COLUMN IF EXISTS script_context"))
    conn.execute(sa.text("ALTER TABLE scripts DROP COLUMN IF EXISTS version"))
    conn.execute(sa.text("ALTER TABLE scripts DROP COLUMN IF EXISTS content"))
    conn.execute(sa.text("ALTER TABLE scripts DROP COLUMN IF EXISTS name"))
    conn.execute(sa.text("ALTER TABLE scripts DROP COLUMN IF EXISTS agent_id"))

    conn.execute(
        sa.text("DROP POLICY IF EXISTS platform_admin_bypass_insert_agents ON agents")
    )
    conn.execute(
        sa.text("DROP POLICY IF EXISTS platform_admin_bypass_agents ON agents")
    )
    conn.execute(sa.text("DROP POLICY IF EXISTS tenant_insert_agents ON agents"))
    conn.execute(sa.text("DROP POLICY IF EXISTS tenant_isolation_agents ON agents"))
    conn.execute(sa.text("DROP TABLE IF EXISTS agents"))
