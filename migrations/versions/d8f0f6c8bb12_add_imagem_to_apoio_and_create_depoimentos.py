"""add imagem to apoio and create depoimentos

Revision ID: d8f0f6c8bb12
Revises: 2f5f0f7b3c45
Create Date: 2025-10-03 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d8f0f6c8bb12"
down_revision = "2f5f0f7b3c45"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("apoios", sa.Column("imagem_path", sa.String(length=255), nullable=True))
    op.create_table(
        "depoimentos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("titulo", sa.String(length=150), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("video", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("depoimentos")
    op.drop_column("apoios", "imagem_path")
