"""add calls table for vapi telephony bridge

Revision ID: g2h3i4j5k6l7
Revises: f1g2h3i4j5k6
Create Date: 2026-03-31 12:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "g2h3i4j5k6l7"
down_revision: Union[str, Sequence[str], None] = "f1g2h3i4j5k6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(
        sa.text("""
        CREATE TABLE IF NOT EXISTS calls (
            id SERIAL PRIMARY KEY,
            org_id VARCHAR(255) NOT NULL,
            vapi_call_id VARCHAR(255) UNIQUE,
            lead_id INTEGER REFERENCES leads(id),
            agent_id INTEGER REFERENCES agents(id),
            campaign_id INTEGER,
            status VARCHAR(50) NOT NULL DEFAULT 'pending',
            duration INTEGER,
            recording_url VARCHAR(500),
            phone_number VARCHAR(20) NOT NULL DEFAULT '',
            transcript TEXT,
            ended_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            soft_delete BOOLEAN DEFAULT FALSE
        )
    """)
    )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_calls_vapi_call_id ON calls(vapi_call_id)"
        )
    )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_calls_phone_number ON calls(phone_number)"
        )
    )
    conn.execute(
        sa.text("CREATE INDEX IF NOT EXISTS idx_calls_org_id ON calls(org_id)")
    )
    conn.execute(sa.text("ALTER TABLE calls ENABLE ROW LEVEL SECURITY"))
    conn.execute(
        sa.text("""
        CREATE POLICY tenant_isolation_calls ON calls
        USING (org_id = current_setting('app.current_org_id', true)::text)
    """)
    )
    conn.execute(
        sa.text("""
        CREATE POLICY tenant_insert_calls ON calls
        FOR INSERT WITH CHECK (org_id = current_setting('app.current_org_id', true)::text)
    """)
    )
    conn.execute(
        sa.text("""
        CREATE POLICY platform_admin_bypass_calls ON calls
        USING (current_setting('app.is_platform_admin', true)::boolean = true)
    """)
    )
    conn.execute(
        sa.text("""
        CREATE POLICY platform_admin_bypass_insert_calls ON calls
        FOR INSERT WITH CHECK (current_setting('app.is_platform_admin', true)::boolean = true)
    """)
    )


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(
        sa.text("DROP POLICY IF EXISTS platform_admin_bypass_insert_calls ON calls")
    )
    conn.execute(sa.text("DROP POLICY IF EXISTS platform_admin_bypass_calls ON calls"))
    conn.execute(sa.text("DROP POLICY IF EXISTS tenant_insert_calls ON calls"))
    conn.execute(sa.text("DROP POLICY IF EXISTS tenant_isolation_calls ON calls"))
    conn.execute(sa.text("DROP TABLE IF EXISTS calls"))
