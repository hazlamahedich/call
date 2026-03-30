"""extend usage_logs with resource tracking columns

Revision ID: a2b3c4d5e6f7
Revises: f1g2h3i4j5k6
Create Date: 2026-03-30 17:55:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "f1g2h3i4j5k6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            ALTER TABLE usage_logs
                ADD COLUMN IF NOT EXISTS resource_type VARCHAR(50) NOT NULL DEFAULT 'call',
                ADD COLUMN IF NOT EXISTS resource_id VARCHAR(255) NOT NULL DEFAULT '',
                ADD COLUMN IF NOT EXISTS action VARCHAR(50) NOT NULL DEFAULT 'call_initiated',
                ADD COLUMN IF NOT EXISTS metadata_json VARCHAR(2000) NOT NULL DEFAULT '{}'
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            ALTER TABLE usage_logs
                DROP COLUMN IF EXISTS resource_type,
                DROP COLUMN IF EXISTS resource_id,
                DROP COLUMN IF EXISTS action,
                DROP COLUMN IF EXISTS metadata_json
            """
        )
    )
