"""Ensure imagem_path column exists on apoios

Revision ID: 4c3b5a12a45b
Revises: d8f0f6c8bb12
Create Date: 2025-10-10 00:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "4c3b5a12a45b"
down_revision = "d8f0f6c8bb12"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE apoios ADD COLUMN IF NOT EXISTS imagem_path VARCHAR(255)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE apoios DROP COLUMN IF EXISTS imagem_path")
