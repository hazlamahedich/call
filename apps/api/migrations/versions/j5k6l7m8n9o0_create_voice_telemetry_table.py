"""create voice_telemetry table for asynchronous event tracking

Revision ID: j5k6l7m8n9o0
Revises: i4j5k6l7m8n9
Create Date: 2026-04-03 10:40:00.000000

Story 2.4: Asynchronous Telemetry Sidecars for Voice Events
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "j5k6l7m8n9o0"
down_revision: Union[str, Sequence[str], None] = "i4j5k6l7m8n9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Create voice_telemetry table with composite indexes
    conn.execute(
        sa.text("""
        CREATE TABLE IF NOT EXISTS voice_telemetry (
            id SERIAL PRIMARY KEY,
            org_id VARCHAR(255) NOT NULL,
            call_id INTEGER REFERENCES calls(id) ON DELETE CASCADE,
            event_type VARCHAR(50) NOT NULL,
            timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
            duration_ms FLOAT,
            audio_level FLOAT,
            confidence_score FLOAT,
            sentiment_score FLOAT,
            provider VARCHAR(30) NOT NULL DEFAULT 'vapi',
            session_metadata JSONB,
            queue_depth_at_capture INTEGER,
            processing_latency_ms FLOAT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            soft_delete BOOLEAN DEFAULT FALSE
        )
    """)
    )

    # Create composite indexes for query performance (AC: 4)
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_voice_telemetry_org_id_timestamp ON voice_telemetry(org_id, timestamp)"
        )
    )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_voice_telemetry_call_id_event_type ON voice_telemetry(call_id, event_type)"
        )
    )

    # Individual indexes for filtering
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_voice_telemetry_call_id ON voice_telemetry(call_id)"
        )
    )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_voice_telemetry_event_type ON voice_telemetry(event_type)"
        )
    )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_voice_telemetry_org_id ON voice_telemetry(org_id)"
        )
    )

    # Enable Row Level Security for tenant isolation
    conn.execute(sa.text("ALTER TABLE voice_telemetry ENABLE ROW LEVEL SECURITY"))

    # Create RLS policies for tenant isolation
    conn.execute(
        sa.text("""
        CREATE POLICY vt_tenant_isolation ON voice_telemetry
        USING (org_id = current_setting('app.current_org_id', true)::text)
    """)
    )
    conn.execute(
        sa.text("""
        CREATE POLICY vt_tenant_insert ON voice_telemetry
        FOR INSERT WITH CHECK (org_id = current_setting('app.current_org_id', true)::text)
    """)
    )
    conn.execute(
        sa.text("""
        CREATE POLICY vt_platform_admin_bypass ON voice_telemetry
        USING (current_setting('app.is_platform_admin', true)::boolean = true)
    """)
    )
    conn.execute(
        sa.text("""
        CREATE POLICY vt_platform_admin_bypass_insert ON voice_telemetry
        FOR INSERT WITH CHECK (current_setting('app.is_platform_admin', true)::boolean = true)
    """)
    )


def downgrade() -> None:
    conn = op.get_bind()

    # Drop RLS policies
    conn.execute(
        sa.text(
            "DROP POLICY IF EXISTS vt_platform_admin_bypass_insert ON voice_telemetry"
        )
    )
    conn.execute(
        sa.text("DROP POLICY IF EXISTS vt_platform_admin_bypass ON voice_telemetry")
    )
    conn.execute(sa.text("DROP POLICY IF EXISTS vt_tenant_insert ON voice_telemetry"))
    conn.execute(sa.text("DROP POLICY IF EXISTS vt_tenant_isolation ON voice_telemetry"))

    # Drop table (cascades to indexes automatically)
    conn.execute(sa.text("DROP TABLE IF EXISTS voice_telemetry"))
