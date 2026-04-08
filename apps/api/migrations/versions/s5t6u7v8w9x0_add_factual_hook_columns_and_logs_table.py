"""add factual hook columns and logs table

Revision ID: s5t6u7v8w9x0
Revises: r4s5t6u7v8w9
Create Date: 2026-04-08

"""

from alembic import op
import sqlalchemy as sa

revision = "s5t6u7v8w9x0"
down_revision = "r4s5t6u7v8w9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "script_lab_turns",
        sa.Column("correction_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "script_lab_turns",
        sa.Column(
            "was_corrected", sa.Boolean(), nullable=False, server_default="false"
        ),
    )

    op.create_table(
        "factual_verification_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.String(255), nullable=False),
        sa.Column("query_hash", sa.String(64), nullable=False),
        sa.Column(
            "was_corrected", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("correction_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("claims_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("claims_supported", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "claims_unsupported", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("claims_errored", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "verification_timed_out",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "total_verification_ms", sa.Float(), nullable=False, server_default="0.0"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("soft_delete", sa.Boolean(), nullable=False, server_default="false"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_fvl_org_id", "factual_verification_logs", ["org_id"])
    op.create_index("idx_fvl_created_at", "factual_verification_logs", ["created_at"])
    op.execute("ALTER TABLE factual_verification_logs FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY fvl_tenant_insert ON factual_verification_logs "
        "FOR INSERT WITH CHECK (org_id = current_setting('app.current_org_id', true)::VARCHAR)"
    )
    op.execute(
        "CREATE POLICY fvl_tenant_select ON factual_verification_logs "
        "FOR SELECT USING (org_id = current_setting('app.current_org_id', true)::VARCHAR)"
    )
    op.execute(
        "CREATE POLICY fvl_admin_bypass ON factual_verification_logs "
        "USING (current_setting('app.is_platform_admin', true)::BOOLEAN = true)"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS fvl_admin_bypass ON factual_verification_logs")
    op.execute("DROP POLICY IF EXISTS fvl_tenant_select ON factual_verification_logs")
    op.execute("DROP POLICY IF EXISTS fvl_tenant_insert ON factual_verification_logs")
    op.drop_table("factual_verification_logs")
    op.drop_column("script_lab_turns", "was_corrected")
    op.drop_column("script_lab_turns", "correction_count")
