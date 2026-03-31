"""add transcript_entries and voice_events tables for transcription pipeline

Revision ID: h3i4j5k6l7m8
Revises: g2h3i4j5k6l7
Create Date: 2026-03-31 22:05:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "h3i4j5k6l7m8"
down_revision: Union[str, Sequence[str], None] = "g2h3i4j5k6l7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(
        sa.text("""
        CREATE TABLE IF NOT EXISTS transcript_entries (
            id SERIAL PRIMARY KEY,
            org_id VARCHAR(255) NOT NULL,
            call_id INTEGER NOT NULL REFERENCES calls(id),
            vapi_call_id VARCHAR(255),
            role VARCHAR(30) NOT NULL,
            text TEXT NOT NULL,
            start_time FLOAT,
            end_time FLOAT,
            confidence FLOAT,
            words_json TEXT,
            received_at TIMESTAMP NOT NULL DEFAULT NOW(),
            vapi_event_timestamp FLOAT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            soft_delete BOOLEAN DEFAULT FALSE
        )
    """)
    )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_te_call_id_start ON transcript_entries(call_id, start_time)"
        )
    )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_te_vapi_call_id ON transcript_entries(vapi_call_id)"
        )
    )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_te_org_id ON transcript_entries(org_id)"
        )
    )
    conn.execute(sa.text("ALTER TABLE transcript_entries ENABLE ROW LEVEL SECURITY"))
    conn.execute(
        sa.text("""
        CREATE POLICY te_tenant_isolation ON transcript_entries
        USING (org_id = current_setting('app.current_org_id', true)::text)
    """)
    )
    conn.execute(
        sa.text("""
        CREATE POLICY te_tenant_insert ON transcript_entries
        FOR INSERT WITH CHECK (org_id = current_setting('app.current_org_id', true)::text)
    """)
    )
    conn.execute(
        sa.text("""
        CREATE POLICY te_platform_admin_bypass ON transcript_entries
        USING (current_setting('app.is_platform_admin', true)::boolean = true)
    """)
    )
    conn.execute(
        sa.text("""
        CREATE POLICY te_platform_admin_bypass_insert ON transcript_entries
        FOR INSERT WITH CHECK (current_setting('app.is_platform_admin', true)::boolean = true)
    """)
    )

    conn.execute(
        sa.text("""
        CREATE TABLE IF NOT EXISTS voice_events (
            id SERIAL PRIMARY KEY,
            org_id VARCHAR(255) NOT NULL,
            call_id INTEGER NOT NULL REFERENCES calls(id),
            vapi_call_id VARCHAR(255),
            event_type VARCHAR(50) NOT NULL,
            speaker VARCHAR(20),
            event_metadata TEXT,
            received_at TIMESTAMP NOT NULL DEFAULT NOW(),
            vapi_event_timestamp FLOAT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            soft_delete BOOLEAN DEFAULT FALSE
        )
    """)
    )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_ve_call_id_type ON voice_events(call_id, event_type)"
        )
    )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_ve_vapi_call_id ON voice_events(vapi_call_id)"
        )
    )
    conn.execute(
        sa.text("CREATE INDEX IF NOT EXISTS idx_ve_org_id ON voice_events(org_id)")
    )
    conn.execute(sa.text("ALTER TABLE voice_events ENABLE ROW LEVEL SECURITY"))
    conn.execute(
        sa.text("""
        CREATE POLICY ve_tenant_isolation ON voice_events
        USING (org_id = current_setting('app.current_org_id', true)::text)
    """)
    )
    conn.execute(
        sa.text("""
        CREATE POLICY ve_tenant_insert ON voice_events
        FOR INSERT WITH CHECK (org_id = current_setting('app.current_org_id', true)::text)
    """)
    )
    conn.execute(
        sa.text("""
        CREATE POLICY ve_platform_admin_bypass ON voice_events
        USING (current_setting('app.is_platform_admin', true)::boolean = true)
    """)
    )
    conn.execute(
        sa.text("""
        CREATE POLICY ve_platform_admin_bypass_insert ON voice_events
        FOR INSERT WITH CHECK (current_setting('app.is_platform_admin', true)::boolean = true)
    """)
    )


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(
        sa.text("DROP POLICY IF EXISTS ve_platform_admin_bypass_insert ON voice_events")
    )
    conn.execute(
        sa.text("DROP POLICY IF EXISTS ve_platform_admin_bypass ON voice_events")
    )
    conn.execute(sa.text("DROP POLICY IF EXISTS ve_tenant_insert ON voice_events"))
    conn.execute(sa.text("DROP POLICY IF EXISTS ve_tenant_isolation ON voice_events"))
    conn.execute(sa.text("DROP TABLE IF EXISTS voice_events"))

    conn.execute(
        sa.text(
            "DROP POLICY IF EXISTS te_platform_admin_bypass_insert ON transcript_entries"
        )
    )
    conn.execute(
        sa.text("DROP POLICY IF EXISTS te_platform_admin_bypass ON transcript_entries")
    )
    conn.execute(
        sa.text("DROP POLICY IF EXISTS te_tenant_insert ON transcript_entries")
    )
    conn.execute(
        sa.text("DROP POLICY IF EXISTS te_tenant_isolation ON transcript_entries")
    )
    conn.execute(sa.text("DROP TABLE IF EXISTS transcript_entries"))
