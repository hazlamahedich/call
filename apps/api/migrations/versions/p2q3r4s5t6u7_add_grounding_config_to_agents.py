"""add grounding config to agents

Revision ID: p2q3r4s5t6u7
Revises: n9o0p1q2r3s4
Create Date: 2026-04-06

Adds grounding_config JSONB, system_prompt_template TEXT,
config_version INTEGER columns to agents table.
Adds grounding_mode VARCHAR(20) to scripts table.
Adds knowledge_base_ids JSONB to agents table.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "p2q3r4s5t6u7"
down_revision = "n9o0p1q2r3s4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agents",
        sa.Column("grounding_config", JSONB, nullable=True),
    )
    op.add_column(
        "agents",
        sa.Column("system_prompt_template", sa.Text, nullable=True),
    )
    op.add_column(
        "agents",
        sa.Column("config_version", sa.Integer, nullable=False, server_default="1"),
    )
    op.add_column(
        "agents",
        sa.Column("knowledge_base_ids", JSONB, nullable=True),
    )
    op.add_column(
        "scripts",
        sa.Column("grounding_mode", sa.String(20), nullable=True),
    )

    op.execute(
        """
        ALTER TABLE agents
        ADD CONSTRAINT chk_grounding_mode
        CHECK (
            grounding_config IS NULL
            OR (grounding_config->>'groundingMode') IN ('strict', 'balanced', 'creative')
        )
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE agents DROP CONSTRAINT IF EXISTS chk_grounding_mode")
    op.drop_column("scripts", "grounding_mode")
    op.drop_column("agents", "knowledge_base_ids")
    op.drop_column("agents", "config_version")
    op.drop_column("agents", "system_prompt_template")
    op.drop_column("agents", "grounding_config")
