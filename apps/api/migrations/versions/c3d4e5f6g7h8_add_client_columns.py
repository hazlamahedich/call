"""add_client_columns

Revision ID: c3d4e5f6g7h8
Revises: a1b2c3d4e5f6
Create Date: 2026-03-30 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c3d4e5f6g7h8"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            ALTER TABLE clients
            ADD COLUMN IF NOT EXISTS name TEXT NOT NULL DEFAULT '',
            ADD COLUMN IF NOT EXISTS agency_id TEXT,
            ADD COLUMN IF NOT EXISTS settings_json TEXT
            """
        )
    )
    conn.execute(
        sa.text(
            """
            ALTER TABLE clients ALTER COLUMN name DROP DEFAULT
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            ALTER TABLE clients
            DROP COLUMN IF EXISTS name,
            DROP COLUMN IF EXISTS agency_id,
            DROP COLUMN IF EXISTS settings_json
            """
        )
    )
