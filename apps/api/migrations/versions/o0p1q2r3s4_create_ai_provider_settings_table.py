"""create ai_provider_settings table

Revision ID: o0p1q2r3s4
Revises: n9o0p1q2r3s4
Create Date: 2026-04-05

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "o0p1q2r3s4"
down_revision: Union[str, Sequence[str], None] = "n9o0p1q2r3s4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_provider_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org_id", sa.String(), nullable=True),
        sa.Column("provider", sa.String(50), server_default="openai"),
        sa.Column("encrypted_api_key", sa.String(500), nullable=True),
        sa.Column(
            "embedding_model", sa.String(100), server_default="text-embedding-3-small"
        ),
        sa.Column("embedding_dimensions", sa.Integer(), server_default="1536"),
        sa.Column("llm_model", sa.String(100), server_default="gpt-4o-mini"),
        sa.Column("connection_status", sa.String(20), server_default="untested"),
        sa.Column("soft_delete", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_ai_provider_settings_org_id", "ai_provider_settings", ["org_id"]
    )

    op.execute("ALTER TABLE ai_provider_settings ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY ai_provider_settings_tenant_policy ON ai_provider_settings "
        "USING (org_id = current_setting('app.current_org_id', true)) "
        "FOR ALL"
    )
    op.execute(
        "CREATE TRIGGER set_ai_provider_settings_org_id "
        "BEFORE INSERT ON ai_provider_settings "
        "FOR EACH ROW EXECUTE FUNCTION set_tenant_org_id()"
    )
    op.execute(
        "CREATE TRIGGER set_ai_provider_settings_timestamps "
        "BEFORE UPDATE ON ai_provider_settings "
        "FOR EACH ROW EXECUTE FUNCTION update_timestamps()"
    )


def downgrade() -> None:
    op.drop_table("ai_provider_settings")
