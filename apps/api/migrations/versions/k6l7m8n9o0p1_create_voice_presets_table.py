"""create voice_presets table with seed data

Revision ID: k6l7m8n9o0p1
Revises: j5k6l7m8n9o0
Create Date: 2026-04-04 19:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "k6l7m8n9o0p1"
down_revision: Union[str, Sequence[str], None] = "j5k6l7m8n9o0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Create voice_presets table
    conn.execute(
        sa.text("""
        CREATE TABLE IF NOT EXISTS voice_presets (
            id SERIAL PRIMARY KEY,
            org_id VARCHAR(255) NOT NULL,
            name VARCHAR(255) NOT NULL,
            use_case VARCHAR(50) NOT NULL,
            voice_id VARCHAR(100) NOT NULL,
            speech_speed FLOAT NOT NULL DEFAULT 1.0,
            stability FLOAT NOT NULL DEFAULT 0.8,
            temperature FLOAT NOT NULL DEFAULT 0.7,
            description VARCHAR(500) DEFAULT '',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            soft_delete BOOLEAN DEFAULT FALSE
        )
    """)
    )

    # Create indexes for performance and tenant isolation
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_voice_presets_org_id ON voice_presets(org_id)"
        )
    )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_voice_presets_use_case ON voice_presets(use_case)"
        )
    )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_voice_presets_composite ON voice_presets(org_id, use_case, sort_order)"
        )
    )

    # Enable Row Level Security
    conn.execute(sa.text("ALTER TABLE voice_presets ENABLE ROW LEVEL SECURITY"))

    # Create RLS policies for tenant isolation
    conn.execute(
        sa.text("""
        CREATE POLICY vp_tenant_isolation ON voice_presets
        USING (org_id = current_setting('app.current_org_id', true)::text)
    """)
    )
    conn.execute(
        sa.text("""
        CREATE POLICY vp_tenant_insert ON voice_presets
        FOR INSERT WITH CHECK (org_id = current_setting('app.current_org_id', true)::text)
    """)
    )
    conn.execute(
        sa.text("""
        CREATE POLICY vp_platform_admin_bypass ON voice_presets
        USING (current_setting('app.is_platform_admin', true)::boolean = true)
    """)
    )
    conn.execute(
        sa.text("""
        CREATE POLICY vp_platform_admin_bypass_insert ON voice_presets
        FOR INSERT WITH CHECK (current_setting('app.is_platform_admin', true)::boolean = true)
    """)
    )

    # Insert seed data for default org
    # Sales presets (5) - High energy, confident tones
    conn.execute(
        sa.text("""
        INSERT INTO voice_presets (org_id, name, use_case, voice_id, speech_speed, stability, temperature, description, is_active, sort_order)
        VALUES
        ('default', 'High Energy', 'sales', 'eleven_turbo_v2', 1.2, 0.6, 0.8, 'Enthusiastic, urgent, confident', TRUE, 1),
        ('default', 'Confident Professional', 'sales', 'eleven_multilingual_v2', 1.1, 0.75, 0.7, 'Professional and self-assured', TRUE, 2),
        ('default', 'Friendly Approachable', 'sales', 'cartesia_supersonic', 1.0, 0.8, 0.75, 'Warm and easy to talk to', TRUE, 3),
        ('default', 'Direct Efficient', 'sales', 'eleven_turbo_v2', 1.15, 0.85, 0.65, 'Straight to the point, respectful', TRUE, 4),
        ('default', 'Urgent Closer', 'sales', 'eleven_turbo_v2', 1.25, 0.55, 0.85, 'High energy sales closer', TRUE, 5)
    """)
    )

    # Support presets (4) - Calm, empathetic tones
    conn.execute(
        sa.text("""
        INSERT INTO voice_presets (org_id, name, use_case, voice_id, speech_speed, stability, temperature, description, is_active, sort_order)
        VALUES
        ('default', 'Calm Reassuring', 'support', 'eleven_multilingual_v2', 0.95, 0.85, 0.6, 'Steady and comforting', TRUE, 6),
        ('default', 'Empathetic Warm', 'support', 'cartesia_supersonic', 0.9, 0.8, 0.7, 'Caring and understanding', TRUE, 7),
        ('default', 'Efficient Problem Solver', 'support', 'eleven_turbo_v2', 1.05, 0.85, 0.65, 'Quick but patient', TRUE, 8),
        ('default', 'Technical Expert', 'support', 'eleven_multilingual_v2', 1.0, 0.9, 0.6, 'Knowledgeable and precise', TRUE, 9)
    """)
    )

    # Marketing presets (4) - Engaging, enthusiastic tones
    conn.execute(
        sa.text("""
        INSERT INTO voice_presets (org_id, name, use_case, voice_id, speech_speed, stability, temperature, description, is_active, sort_order)
        VALUES
        ('default', 'Engaging Storyteller', 'marketing', 'cartesia_supersonic', 1.1, 0.7, 0.85, 'Captivates attention', TRUE, 10),
        ('default', 'Enthusiastic Promoter', 'marketing', 'eleven_turbo_v2', 1.2, 0.65, 0.9, 'High energy and exciting', TRUE, 11),
        ('default', 'Trustworthy Guide', 'marketing', 'eleven_multilingual_v2', 1.0, 0.85, 0.65, 'Reliable and informative', TRUE, 12),
        ('default', 'Casual Friendly', 'marketing', 'cartesia_supersonic', 0.95, 0.75, 0.8, 'Relaxed and approachable', TRUE, 13)
    """)
    )


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(
        sa.text(
            "DROP POLICY IF EXISTS vp_platform_admin_bypass_insert ON voice_presets"
        )
    )
    conn.execute(
        sa.text("DROP POLICY IF EXISTS vp_platform_admin_bypass ON voice_presets")
    )
    conn.execute(sa.text("DROP POLICY IF EXISTS vp_tenant_insert ON voice_presets"))
    conn.execute(sa.text("DROP POLICY IF EXISTS vp_tenant_isolation ON voice_presets"))
    conn.execute(sa.text("DROP TABLE IF EXISTS voice_presets"))
