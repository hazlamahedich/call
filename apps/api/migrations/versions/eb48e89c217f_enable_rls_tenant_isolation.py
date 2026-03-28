"""enable_rls_tenant_isolation

Revision ID: eb48e89c217f
Revises:
Create Date: 2026-03-28 13:05:12.28+10:11:45

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "eb48e89c217f"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TENANT_TABLES = [
    "agencies",
    "clients",
    "leads",
    "calls",
    "scripts",
    "knowledge_bases",
    "campaigns",
    "usage_logs",
]


def upgrade() -> None:
    conn = op.get_bind()

    for table_name in TENANT_TABLES:
        conn.execute(
            sa.text(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id SERIAL PRIMARY KEY,
                org_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                soft_delete BOOLEAN DEFAULT FALSE
            )
        """)
        )
        conn.execute(
            sa.text(f"""
            CREATE INDEX IF NOT EXISTS idx_{table_name}_org_id
            ON {table_name}(org_id)
        """)
        )
        conn.execute(
            sa.text(f"""
            ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY
        """)
        )
        conn.execute(
            sa.text(f"""
            CREATE POLICY tenant_isolation_{table_name} ON {table_name}
            USING (org_id = current_setting('app.current_org_id', true)::text)
        """)
        )
        conn.execute(
            sa.text(f"""
            CREATE POLICY tenant_insert_{table_name} ON {table_name}
            FOR INSERT WITH CHECK (org_id = current_setting('app.current_org_id', true)::text)
        """)
        )
        conn.execute(
            sa.text(f"""
            CREATE POLICY platform_admin_bypass ON {table_name}
            USING (current_setting('app.is_platform_admin', true)::boolean = true)
        """)
        )
        conn.execute(
            sa.text(f"""
            CREATE POLICY platform_admin_bypass_insert ON {table_name}
            FOR INSERT WITH CHECK (current_setting('app.is_platform_admin', true)::boolean = true)
        """)
        )


def downgrade() -> None:
    conn = op.get_bind()

    for table_name in TENANT_TABLES:
        conn.execute(
            sa.text(
                f"DROP POLICY IF EXISTS platform_admin_bypass_insert ON {table_name}"
            )
        )
        conn.execute(
            sa.text(f"DROP POLICY IF EXISTS platform_admin_bypass ON {table_name}")
        )
        conn.execute(
            sa.text(f"""
            DROP POLICY IF EXISTS tenant_insert_{table_name} ON {table_name}
        """)
        )
        conn.execute(
            sa.text(f"""
            DROP POLICY IF EXISTS tenant_isolation_{table_name} ON {table_name}
        """)
        )
        conn.execute(
            sa.text(f"""
            ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY
        """)
        )
        conn.execute(sa.text(f"DROP INDEX IF EXISTS idx_{table_name}_org_id"))
        conn.execute(sa.text(f"DROP TABLE IF EXISTS {table_name}"))
