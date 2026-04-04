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

    # Add preset_id foreign key column (nullable for backward compatibility)
    conn.execute(
        sa.text("""
        ALTER TABLE agents ADD COLUMN IF NOT EXISTS preset_id INTEGER
        REFERENCES voice_presets(id) ON DELETE SET NULL
    """)
    )

    # Add use_advanced_mode boolean column
    conn.execute(
        sa.text("""
        ALTER TABLE agents ADD COLUMN IF NOT EXISTS use_advanced_mode BOOLEAN
        NOT NULL DEFAULT FALSE
    """)
    )

    # Add speech_speed column
    conn.execute(
        sa.text("""
        ALTER TABLE agents ADD COLUMN IF NOT EXISTS speech_speed FLOAT
        NOT NULL DEFAULT 1.0
    """)
    )

    # Add stability column
    conn.execute(
        sa.text("""
        ALTER TABLE agents ADD COLUMN IF NOT EXISTS stability FLOAT
        NOT NULL DEFAULT 0.8
    """)
    )

    # Add temperature column
    conn.execute(
        sa.text("""
        ALTER TABLE agents ADD COLUMN IF NOT EXISTS temperature FLOAT
        NOT NULL DEFAULT 0.7
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
