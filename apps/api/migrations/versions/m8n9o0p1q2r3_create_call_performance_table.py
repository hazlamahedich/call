"""create call_performance table for preset recommendations

Revision ID: m8n9o0p1q2r3
Revises: l7m8n9o0p1q2
Create Date: 2026-04-04 20:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "m8n9o0p1q2r3"
down_revision: Union[str, Sequence[str], None] = "l7m8n9o0p1q2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # SECURITY NOTE: This migration uses raw SQL with hardcoded literal values.
    # All values in this migration are constants and safe from SQL injection.
    # DO NOT modify this code to include dynamic values without proper parameterization.

    # Create call_performance table
    conn.execute(
        sa.text("""
        CREATE TABLE IF NOT EXISTS call_performance (
            id SERIAL PRIMARY KEY,
            org_id VARCHAR(255) NOT NULL,
            call_id VARCHAR(100) NOT NULL,
            agent_id INTEGER,
            preset_id INTEGER,
            use_case VARCHAR(50) NOT NULL,
            duration_seconds FLOAT NOT NULL,
            was_answered BOOLEAN NOT NULL,
            was_connected BOOLEAN NOT NULL,
            has_callback BOOLEAN NOT NULL DEFAULT FALSE,
            outcome VARCHAR(50) NOT NULL,
            sentiment_score FLOAT,
            call_started_at TIMESTAMP NOT NULL,
            call_ended_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            soft_delete BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (preset_id) REFERENCES voice_presets(id) ON DELETE SET NULL
        )
    """)
    )

    # Create indexes for performance queries
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_call_performance_org_id ON call_performance(org_id)"
        )
    )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_call_performance_use_case ON call_performance(use_case)"
        )
    )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_call_performance_preset_id ON call_performance(preset_id)"
        )
    )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_call_performance_call_started_at ON call_performance(call_started_at)"
        )
    )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_call_performance_composite ON call_performance(org_id, use_case, call_started_at)"
        )
    )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_call_performance_soft_delete ON call_performance(soft_delete)"
        )
    )

    # Enable Row Level Security
    conn.execute(sa.text("ALTER TABLE call_performance ENABLE ROW LEVEL SECURITY"))

    # Create RLS policies for tenant isolation
    conn.execute(
        sa.text("""
        CREATE POLICY cp_tenant_isolation ON call_performance
        USING (org_id = current_setting('app.current_org_id', true)::text)
    """)
    )
    conn.execute(
        sa.text("""
        CREATE POLICY cp_tenant_insert ON call_performance
        FOR INSERT WITH CHECK (org_id = current_setting('app.current_org_id', true)::text)
    """)
    )
    conn.execute(
        sa.text("""
        CREATE POLICY cp_platform_admin_bypass ON call_performance
        USING (current_setting('app.is_platform_admin', true)::boolean = true)
    """)
    )
    conn.execute(
        sa.text("""
        CREATE POLICY cp_platform_admin_bypass_insert ON call_performance
        FOR INSERT WITH CHECK (current_setting('app.is_platform_admin', true)::boolean = true)
    """)
    )


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(
        sa.text(
            "DROP POLICY IF EXISTS cp_platform_admin_bypass_insert ON call_performance"
        )
    )
    conn.execute(
        sa.text("DROP POLICY IF EXISTS cp_platform_admin_bypass ON call_performance")
    )
    conn.execute(sa.text("DROP POLICY IF EXISTS cp_tenant_insert ON call_performance"))
    conn.execute(sa.text("DROP POLICY IF EXISTS cp_tenant_isolation ON call_performance"))
    conn.execute(sa.text("DROP TABLE IF EXISTS call_performance"))
