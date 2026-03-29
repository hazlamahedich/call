"""add agency_branding table

Revision ID: a1b2c3d4e5f6
Revises: eb48e89c217f
Create Date: 2026-03-29 22:00:00.00+08:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "eb48e89c217f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "agency_branding"


def upgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name

    op.create_table(
        TABLE_NAME,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("org_id", sa.String, nullable=False, index=True),
        sa.Column("logo_url", sa.String, nullable=True),
        sa.Column(
            "primary_color", sa.String(7), nullable=False, server_default="#10B981"
        ),
        sa.Column("custom_domain", sa.String(255), nullable=True),
        sa.Column(
            "domain_verified",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
        sa.Column("brand_name", sa.String(255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "soft_delete", sa.Boolean, nullable=False, server_default=sa.text("FALSE")
        ),
    )

    if dialect == "postgresql":
        conn.execute(sa.text(f"ALTER TABLE {TABLE_NAME} ENABLE ROW LEVEL SECURITY"))
        conn.execute(sa.text(f"ALTER TABLE {TABLE_NAME} FORCE ROW LEVEL SECURITY"))
        conn.execute(
            sa.text(
                f"""
            CREATE POLICY tenant_isolation_{TABLE_NAME} ON {TABLE_NAME}
                USING (org_id = current_setting('app.current_org_id', true)::text)
                WITH CHECK (org_id = current_setting('app.current_org_id', true)::text)
        """
            )
        )
        conn.execute(
            sa.text(
                f"""
            CREATE POLICY platform_admin_bypass ON {TABLE_NAME}
                USING (current_setting('app.is_platform_admin', true)::boolean = true)
                WITH CHECK (current_setting('app.is_platform_admin', true)::boolean = true)
        """
            )
        )
        conn.execute(
            sa.text(
                f"""
            CREATE TRIGGER trg_agency_branding_set_org_id
                BEFORE INSERT ON {TABLE_NAME}
                FOR EACH ROW
                EXECUTE FUNCTION set_org_id_from_context()
        """
            )
        )


def downgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect == "postgresql":
        conn.execute(
            sa.text(
                f"DROP TRIGGER IF EXISTS trg_agency_branding_set_org_id ON {TABLE_NAME}"
            )
        )
        conn.execute(
            sa.text(f"DROP POLICY IF EXISTS platform_admin_bypass ON {TABLE_NAME}")
        )
        conn.execute(
            sa.text(
                f"DROP POLICY IF EXISTS tenant_isolation_{TABLE_NAME} ON {TABLE_NAME}"
            )
        )
        conn.execute(sa.text(f"ALTER TABLE {TABLE_NAME} DISABLE ROW LEVEL SECURITY"))

    op.drop_table(TABLE_NAME)
