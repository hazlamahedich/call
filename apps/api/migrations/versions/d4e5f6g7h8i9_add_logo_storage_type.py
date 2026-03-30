"""add logo_storage_type to agency_branding

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2026-03-30 13:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d4e5f6g7h8i9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6g7h8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "agency_branding",
        sa.Column("logo_storage_type", sa.String(16), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("agency_branding", "logo_storage_type")
