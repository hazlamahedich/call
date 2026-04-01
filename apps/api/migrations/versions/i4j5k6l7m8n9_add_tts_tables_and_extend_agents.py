"""add tts_requests, tts_provider_switches tables and extend agents with TTS fields

Revision ID: i4j5k6l7m8n9
Revises: h3i4j5k6l7m8
Create Date: 2026-04-01 21:15:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "i4j5k6l7m8n9"
down_revision: Union[str, Sequence[str], None] = "h3i4j5k6l7m8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(
        sa.text("""
        CREATE TABLE IF NOT EXISTS tts_requests (
            id SERIAL PRIMARY KEY,
            org_id VARCHAR(255) NOT NULL,
            call_id INTEGER REFERENCES calls(id) ON DELETE CASCADE,
            vapi_call_id VARCHAR(255),
            provider VARCHAR(30) NOT NULL,
            voice_id VARCHAR(100) NOT NULL DEFAULT '',
            text_length INTEGER NOT NULL DEFAULT 0,
            latency_ms FLOAT,
            status VARCHAR(20) NOT NULL,
            error_message TEXT,
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
            "CREATE INDEX IF NOT EXISTS idx_tts_requests_call_id ON tts_requests(call_id)"
        )
    )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_tts_requests_vapi_call_id ON tts_requests(vapi_call_id)"
        )
    )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_tts_requests_call_id_provider ON tts_requests(call_id, provider)"
        )
    )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_tts_requests_org_id ON tts_requests(org_id)"
        )
    )
    conn.execute(sa.text("ALTER TABLE tts_requests ENABLE ROW LEVEL SECURITY"))
    conn.execute(
        sa.text("""
        CREATE POLICY ttr_tenant_isolation ON tts_requests
        USING (org_id = current_setting('app.current_org_id', true)::text)
    """)
    )
    conn.execute(
        sa.text("""
        CREATE POLICY ttr_tenant_insert ON tts_requests
        FOR INSERT WITH CHECK (org_id = current_setting('app.current_org_id', true)::text)
    """)
    )
    conn.execute(
        sa.text("""
        CREATE POLICY ttr_platform_admin_bypass ON tts_requests
        USING (current_setting('app.is_platform_admin', true)::boolean = true)
    """)
    )
    conn.execute(
        sa.text("""
        CREATE POLICY ttr_platform_admin_bypass_insert ON tts_requests
        FOR INSERT WITH CHECK (current_setting('app.is_platform_admin', true)::boolean = true)
    """)
    )

    conn.execute(
        sa.text("""
        CREATE TABLE IF NOT EXISTS tts_provider_switches (
            id SERIAL PRIMARY KEY,
            org_id VARCHAR(255) NOT NULL,
            call_id INTEGER REFERENCES calls(id) ON DELETE CASCADE,
            vapi_call_id VARCHAR(255),
            from_provider VARCHAR(30) NOT NULL,
            to_provider VARCHAR(30) NOT NULL,
            reason VARCHAR(100) NOT NULL,
            consecutive_slow_count INTEGER NOT NULL DEFAULT 0,
            last_latency_ms FLOAT,
            switched_at TIMESTAMP NOT NULL DEFAULT NOW(),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            soft_delete BOOLEAN DEFAULT FALSE
        )
    """)
    )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_tts_switches_call_id ON tts_provider_switches(call_id)"
        )
    )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_tts_switches_vapi_call_id ON tts_provider_switches(vapi_call_id)"
        )
    )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_tts_provider_switches_call_id_switched_at ON tts_provider_switches(call_id, switched_at)"
        )
    )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_tts_switches_org_id ON tts_provider_switches(org_id)"
        )
    )
    conn.execute(sa.text("ALTER TABLE tts_provider_switches ENABLE ROW LEVEL SECURITY"))
    conn.execute(
        sa.text("""
        CREATE POLICY tps_tenant_isolation ON tts_provider_switches
        USING (org_id = current_setting('app.current_org_id', true)::text)
    """)
    )
    conn.execute(
        sa.text("""
        CREATE POLICY tps_tenant_insert ON tts_provider_switches
        FOR INSERT WITH CHECK (org_id = current_setting('app.current_org_id', true)::text)
    """)
    )
    conn.execute(
        sa.text("""
        CREATE POLICY tps_platform_admin_bypass ON tts_provider_switches
        USING (current_setting('app.is_platform_admin', true)::boolean = true)
    """)
    )
    conn.execute(
        sa.text("""
        CREATE POLICY tps_platform_admin_bypass_insert ON tts_provider_switches
        FOR INSERT WITH CHECK (current_setting('app.is_platform_admin', true)::boolean = true)
    """)
    )

    conn.execute(
        sa.text(
            "ALTER TABLE agents ADD COLUMN IF NOT EXISTS tts_provider VARCHAR(30) NOT NULL DEFAULT 'auto'"
        )
    )
    conn.execute(
        sa.text(
            "ALTER TABLE agents ADD COLUMN IF NOT EXISTS tts_voice_model VARCHAR(100) NOT NULL DEFAULT ''"
        )
    )
    conn.execute(
        sa.text(
            "ALTER TABLE agents ADD COLUMN IF NOT EXISTS fallback_tts_provider VARCHAR(30)"
        )
    )


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(
        sa.text("ALTER TABLE agents DROP COLUMN IF EXISTS fallback_tts_provider")
    )
    conn.execute(sa.text("ALTER TABLE agents DROP COLUMN IF EXISTS tts_voice_model"))
    conn.execute(sa.text("ALTER TABLE agents DROP COLUMN IF EXISTS tts_provider"))

    conn.execute(
        sa.text(
            "DROP POLICY IF EXISTS tps_platform_admin_bypass_insert ON tts_provider_switches"
        )
    )
    conn.execute(
        sa.text(
            "DROP POLICY IF EXISTS tps_platform_admin_bypass ON tts_provider_switches"
        )
    )
    conn.execute(
        sa.text("DROP POLICY IF EXISTS tps_tenant_insert ON tts_provider_switches")
    )
    conn.execute(
        sa.text("DROP POLICY IF EXISTS tps_tenant_isolation ON tts_provider_switches")
    )
    conn.execute(sa.text("DROP TABLE IF EXISTS tts_provider_switches"))

    conn.execute(
        sa.text(
            "DROP POLICY IF EXISTS ttr_platform_admin_bypass_insert ON tts_requests"
        )
    )
    conn.execute(
        sa.text("DROP POLICY IF EXISTS ttr_platform_admin_bypass ON tts_requests")
    )
    conn.execute(sa.text("DROP POLICY IF EXISTS ttr_tenant_insert ON tts_requests"))
    conn.execute(sa.text("DROP POLICY IF EXISTS ttr_tenant_isolation ON tts_requests"))
    conn.execute(sa.text("DROP TABLE IF EXISTS tts_requests"))
