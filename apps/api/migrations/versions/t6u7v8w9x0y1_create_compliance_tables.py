"""create compliance tables (dnc_check_logs, blocklist_entries) and extend calls

Revision ID: t6u7v8w9x0y1
Revises: s5t6u7v8w9x0
Create Date: 2026-04-10

"""

from alembic import op
import sqlalchemy as sa

revision = "t6u7v8w9x0y1"
down_revision = "s5t6u7v8w9x0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "calls",
        sa.Column("compliance_status", sa.String(30), nullable=True),
    )
    op.add_column(
        "calls",
        sa.Column("state_code", sa.String(5), nullable=True),
    )
    op.add_column(
        "calls",
        sa.Column(
            "consent_captured",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "calls",
        sa.Column(
            "graceful_goodnight_triggered",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )

    op.create_table(
        "dnc_check_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.String(255), nullable=False),
        sa.Column("phone_number", sa.String(20), nullable=False),
        sa.Column("check_type", sa.String(20), nullable=False),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("result", sa.String(20), nullable=False),
        sa.Column("lead_id", sa.BigInteger(), nullable=True),
        sa.Column("campaign_id", sa.BigInteger(), nullable=True),
        sa.Column("call_id", sa.BigInteger(), nullable=True),
        sa.Column("response_time_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("raw_response", sa.Text(), nullable=True),
        sa.Column(
            "checked_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("soft_delete", sa.Boolean(), nullable=False, server_default="false"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"]),
        sa.ForeignKeyConstraint(["call_id"], ["calls.id"]),
    )
    op.create_index(
        "ix_dnc_check_logs_phone_number", "dnc_check_logs", ["phone_number"]
    )
    op.create_index(
        "ix_dnc_check_logs_org_phone", "dnc_check_logs", ["org_id", "phone_number"]
    )
    op.create_index("ix_dnc_check_logs_call_id", "dnc_check_logs", ["call_id"])
    op.create_index("ix_dnc_check_logs_org_id", "dnc_check_logs", ["org_id"])
    op.execute("ALTER TABLE dnc_check_logs FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY dcl_tenant_insert ON dnc_check_logs "
        "FOR INSERT WITH CHECK (org_id = current_setting('app.current_org_id', true)::VARCHAR)"
    )
    op.execute(
        "CREATE POLICY dcl_tenant_select ON dnc_check_logs "
        "FOR SELECT USING (org_id = current_setting('app.current_org_id', true)::VARCHAR)"
    )
    op.execute(
        "CREATE POLICY dcl_admin_bypass ON dnc_check_logs "
        "USING (current_setting('app.is_platform_admin', true)::BOOLEAN = true)"
    )

    op.create_table(
        "blocklist_entries",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.String(255), nullable=False),
        sa.Column("phone_number", sa.String(20), nullable=False),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("lead_id", sa.BigInteger(), nullable=True),
        sa.Column("auto_blocked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("soft_delete", sa.Boolean(), nullable=False, server_default="false"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"]),
        sa.UniqueConstraint("org_id", "phone_number", name="uq_blocklist_org_phone"),
    )
    op.create_index(
        "ix_blocklist_entries_phone_number", "blocklist_entries", ["phone_number"]
    )
    op.create_index("ix_blocklist_entries_org_id", "blocklist_entries", ["org_id"])
    op.execute("ALTER TABLE blocklist_entries FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY be_tenant_insert ON blocklist_entries "
        "FOR INSERT WITH CHECK (org_id = current_setting('app.current_org_id', true)::VARCHAR)"
    )
    op.execute(
        "CREATE POLICY be_tenant_select ON blocklist_entries "
        "FOR SELECT USING (org_id = current_setting('app.current_org_id', true)::VARCHAR)"
    )
    op.execute(
        "CREATE POLICY be_tenant_update ON blocklist_entries "
        "FOR UPDATE USING (org_id = current_setting('app.current_org_id', true)::VARCHAR)"
    )
    op.execute(
        "CREATE POLICY be_admin_bypass ON blocklist_entries "
        "USING (current_setting('app.is_platform_admin', true)::BOOLEAN = true)"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS be_admin_bypass ON blocklist_entries")
    op.execute("DROP POLICY IF EXISTS be_tenant_update ON blocklist_entries")
    op.execute("DROP POLICY IF EXISTS be_tenant_select ON blocklist_entries")
    op.execute("DROP POLICY IF EXISTS be_tenant_insert ON blocklist_entries")
    op.drop_table("blocklist_entries")

    op.execute("DROP POLICY IF EXISTS dcl_admin_bypass ON dnc_check_logs")
    op.execute("DROP POLICY IF EXISTS dcl_tenant_select ON dnc_check_logs")
    op.execute("DROP POLICY IF EXISTS dcl_tenant_insert ON dnc_check_logs")
    op.drop_table("dnc_check_logs")

    op.drop_column("calls", "graceful_goodnight_triggered")
    op.drop_column("calls", "consent_captured")
    op.drop_column("calls", "state_code")
    op.drop_column("calls", "compliance_status")
