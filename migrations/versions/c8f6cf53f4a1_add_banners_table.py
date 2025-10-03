"""add banners table

Revision ID: c8f6cf53f4a1
Revises: 576017431647
Create Date: 2025-10-03 19:18:47.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c8f6cf53f4a1"
down_revision = "576017431647"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "banners",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("titulo", sa.String(length=255), nullable=False),
        sa.Column("descricao", sa.String(length=512), nullable=True),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("imagem_path", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("banners")
