"""add preset_id and use_advanced_mode to agents table

Revision ID: l7m8n9o0p1q2
Revises: k6l7m8n9o0p1
Create Date: 2026-04-04 19:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "l7m8n9o0p1q2"
down_revision: Union[str, Sequence[str], None] = "k6l7m8n9o0p1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Add columns as nullable first for backward compatibility with existing data
    conn.execute(
        sa.text("""
        ALTER TABLE agents ADD COLUMN IF NOT EXISTS preset_id INTEGER
        REFERENCES voice_presets(id) ON DELETE SET NULL
    """)
    )

    conn.execute(
        sa.text("""
        ALTER TABLE agents ADD COLUMN IF NOT EXISTS use_advanced_mode BOOLEAN
    """)
    )

    conn.execute(
        sa.text("""
        ALTER TABLE agents ADD COLUMN IF NOT EXISTS speech_speed FLOAT
    """)
    )

    conn.execute(
        sa.text("""
        ALTER TABLE agents ADD COLUMN IF NOT EXISTS stability FLOAT
    """)
    )

    conn.execute(
        sa.text("""
        ALTER TABLE agents ADD COLUMN IF NOT EXISTS temperature FLOAT
    """)
    )

    # Update existing rows with defaults
    conn.execute(
        sa.text("""
        UPDATE agents
        SET use_advanced_mode = FALSE,
            speech_speed = 1.0,
            stability = 0.8,
            temperature = 0.7
        WHERE use_advanced_mode IS NULL
    """)
    )

    # Now make columns NOT NULL
    conn.execute(
        sa.text("""
        ALTER TABLE agents ALTER COLUMN use_advanced_mode SET NOT NULL
    """)
    )

    conn.execute(
        sa.text("""
        ALTER TABLE agents ALTER COLUMN speech_speed SET NOT NULL
    """)
    )

    conn.execute(
        sa.text("""
        ALTER TABLE agents ALTER COLUMN stability SET NOT NULL
    """)
    )

    conn.execute(
        sa.text("""
        ALTER TABLE agents ALTER COLUMN temperature SET NOT NULL
    """)
    )

    # Add index for preset lookups
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_agents_preset_id ON agents(preset_id)"
        )
    )


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text("ALTER TABLE agents DROP COLUMN IF EXISTS use_advanced_mode"))
    conn.execute(sa.text("ALTER TABLE agents DROP COLUMN IF EXISTS preset_id"))
