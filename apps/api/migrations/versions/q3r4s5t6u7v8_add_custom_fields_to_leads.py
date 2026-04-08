"""add custom_fields to leads

Revision ID: q3r4s5t6u7v8
Revises: p2q3r4s5t6u7
Create Date: 2026-04-08

Adds custom_fields JSONB column to leads table
for hyper-personalization variable injection (Story 3.4).
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "q3r4s5t6u7v8"
down_revision = "p2q3r4s5t6u7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "leads",
        sa.Column(
            "custom_fields", JSONB, nullable=True, server_default=sa.text("NULL")
        ),
    )


def downgrade() -> None:
    op.drop_column("leads", "custom_fields")
