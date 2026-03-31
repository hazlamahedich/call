"""add calls table for vapi telephony bridge

Revision ID: g2h3i4j5k6l7
Revises: f1g2h3i4j5k6
Create Date: 2026-03-31 12:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "g2h3i4j5k6l7"
down_revision: Union[str, Sequence[str], None] = "b3c4d5e6f7g8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(
        sa.text("ALTER TABLE calls ADD COLUMN IF NOT EXISTS vapi_call_id VARCHAR(255)")
    )
    conn.execute(
        sa.text(
            "ALTER TABLE calls ADD COLUMN IF NOT EXISTS lead_id INTEGER REFERENCES leads(id)"
        )
    )
    conn.execute(
        sa.text(
            "ALTER TABLE calls ADD COLUMN IF NOT EXISTS agent_id INTEGER REFERENCES agents(id)"
        )
    )
    conn.execute(
        sa.text("ALTER TABLE calls ADD COLUMN IF NOT EXISTS campaign_id INTEGER")
    )
    conn.execute(
        sa.text(
            "ALTER TABLE calls ADD COLUMN IF NOT EXISTS status VARCHAR(50) NOT NULL DEFAULT 'pending'"
        )
    )
    conn.execute(sa.text("ALTER TABLE calls ADD COLUMN IF NOT EXISTS duration INTEGER"))
    conn.execute(
        sa.text("ALTER TABLE calls ADD COLUMN IF NOT EXISTS recording_url VARCHAR(500)")
    )
    conn.execute(
        sa.text(
            "ALTER TABLE calls ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20) NOT NULL DEFAULT ''"
        )
    )
    conn.execute(sa.text("ALTER TABLE calls ADD COLUMN IF NOT EXISTS transcript TEXT"))
    conn.execute(
        sa.text("ALTER TABLE calls ADD COLUMN IF NOT EXISTS ended_at TIMESTAMP")
    )

    conn.execute(
        sa.text(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_calls_vapi_call_id ON calls(vapi_call_id)"
        )
    )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_calls_phone_number ON calls(phone_number)"
        )
    )


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text("DROP INDEX IF EXISTS idx_calls_phone_number"))
    conn.execute(sa.text("DROP INDEX IF EXISTS idx_calls_vapi_call_id"))
    conn.execute(sa.text("ALTER TABLE calls DROP COLUMN IF EXISTS ended_at"))
    conn.execute(sa.text("ALTER TABLE calls DROP COLUMN IF EXISTS transcript"))
    conn.execute(sa.text("ALTER TABLE calls DROP COLUMN IF EXISTS phone_number"))
    conn.execute(sa.text("ALTER TABLE calls DROP COLUMN IF EXISTS recording_url"))
    conn.execute(sa.text("ALTER TABLE calls DROP COLUMN IF EXISTS duration"))
    conn.execute(sa.text("ALTER TABLE calls DROP COLUMN IF EXISTS status"))
    conn.execute(sa.text("ALTER TABLE calls DROP COLUMN IF EXISTS campaign_id"))
    conn.execute(sa.text("ALTER TABLE calls DROP COLUMN IF EXISTS agent_id"))
    conn.execute(sa.text("ALTER TABLE calls DROP COLUMN IF EXISTS lead_id"))
    conn.execute(sa.text("ALTER TABLE calls DROP COLUMN IF EXISTS vapi_call_id"))
