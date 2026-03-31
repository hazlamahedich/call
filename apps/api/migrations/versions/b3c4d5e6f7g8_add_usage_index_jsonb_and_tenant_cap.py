"""add usage index, jsonb migration, and tenant cap override

Revision ID: b3c4d5e6f7g8
Revises: a2b3c4d5e6f7
Create Date: 2026-03-31 08:45:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b3c4d5e6f7g8"
down_revision: Union[str, Sequence[str], None] = "a2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_usage_logs_org_created_action
            ON usage_logs(org_id, created_at, action)
            """
        )
    )

    conn.execute(
        sa.text(
            """
            ALTER TABLE usage_logs
            ALTER COLUMN metadata_json TYPE JSONB
            USING metadata_json::jsonb
            """
        )
    )
    conn.execute(
        sa.text(
            "ALTER TABLE usage_logs ALTER COLUMN metadata_json SET DEFAULT '{}'::jsonb"
        )
    )

    conn.execute(
        sa.text(
            """
            ALTER TABLE agencies
            ADD COLUMN IF NOT EXISTS monthly_call_cap INTEGER DEFAULT NULL
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text("ALTER TABLE agencies DROP COLUMN IF EXISTS monthly_call_cap"))

    conn.execute(
        sa.text("ALTER TABLE usage_logs ALTER COLUMN metadata_json SET DEFAULT '{}'")
    )
    conn.execute(
        sa.text(
            """
            ALTER TABLE usage_logs
            ALTER COLUMN metadata_json TYPE VARCHAR(2000)
            USING metadata_json::text
            """
        )
    )

    conn.execute(sa.text("DROP INDEX IF EXISTS idx_usage_logs_org_created_action"))
