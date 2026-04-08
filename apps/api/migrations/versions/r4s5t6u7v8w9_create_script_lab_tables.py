"""create script lab tables

Revision ID: r4s5t6u7v8w9
Revises: q3r4s5t6u7v8
Create Date: 2026-04-08

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "r4s5t6u7v8w9"
down_revision = "q3r4s5t6u7v8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "script_lab_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("script_id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=True),
        sa.Column("scenario_overlay", JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("turn_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("soft_delete", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["script_id"], ["scripts.id"]),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"]),
    )

    op.execute("ALTER TABLE script_lab_sessions ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation_script_lab_sessions ON script_lab_sessions "
        "USING (org_id = current_setting('app.current_org_id', true)::text)"
    )
    op.execute(
        "CREATE POLICY platform_admin_bypass ON script_lab_sessions "
        "USING (true) WITH CHECK (true)"
    )
    op.execute(
        "CREATE TRIGGER set_org_id_script_lab_sessions "
        "BEFORE INSERT ON script_lab_sessions "
        "FOR EACH ROW EXECUTE FUNCTION set_org_id_from_context()"
    )
    op.create_index(
        "ix_script_lab_sessions_org_id",
        "script_lab_sessions",
        ["org_id"],
    )

    op.create_table(
        "script_lab_turns",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("turn_number", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_attributions", JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("grounding_confidence", sa.Float(), nullable=True),
        sa.Column(
            "low_confidence_warning",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column("soft_delete", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["session_id"], ["script_lab_sessions.id"]),
        sa.CheckConstraint(
            "role IN ('user', 'assistant')",
            name="ck_script_lab_turns_role",
        ),
    )

    op.execute("ALTER TABLE script_lab_turns ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation_script_lab_turns ON script_lab_turns "
        "USING (org_id = current_setting('app.current_org_id', true)::text)"
    )
    op.execute(
        "CREATE POLICY platform_admin_bypass ON script_lab_turns "
        "USING (true) WITH CHECK (true)"
    )
    op.execute(
        "CREATE TRIGGER set_org_id_script_lab_turns "
        "BEFORE INSERT ON script_lab_turns "
        "FOR EACH ROW EXECUTE FUNCTION set_org_id_from_context()"
    )
    op.create_index(
        "ix_script_lab_turns_session_turn",
        "script_lab_turns",
        ["session_id", "turn_number"],
    )
    op.create_index(
        "ix_script_lab_turns_org_id",
        "script_lab_turns",
        ["org_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_script_lab_turns_org_id")
    op.drop_index("ix_script_lab_turns_session_turn")
    op.execute("DROP TRIGGER IF EXISTS set_org_id_script_lab_turns ON script_lab_turns")
    op.execute("DROP POLICY IF EXISTS platform_admin_bypass ON script_lab_turns")
    op.execute(
        "DROP POLICY IF EXISTS tenant_isolation_script_lab_turns ON script_lab_turns"
    )
    op.execute("ALTER TABLE script_lab_turns DISABLE ROW LEVEL SECURITY")
    op.drop_table("script_lab_turns")

    op.drop_index("ix_script_lab_sessions_org_id")
    op.execute(
        "DROP TRIGGER IF EXISTS set_org_id_script_lab_sessions ON script_lab_sessions"
    )
    op.execute("DROP POLICY IF EXISTS platform_admin_bypass ON script_lab_sessions")
    op.execute(
        "DROP POLICY IF EXISTS tenant_isolation_script_lab_sessions ON script_lab_sessions"
    )
    op.execute("ALTER TABLE script_lab_sessions DISABLE ROW LEVEL SECURITY")
    op.drop_table("script_lab_sessions")
