"""Rename institutional tables to singular names"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "2f5f0f7b3c45"
down_revision = "c8f6cf53f4a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.rename_table("textos_institucionais", "textos")
    op.rename_table("galerias", "galeria")
    op.rename_table("transparencias", "transparencia")


def downgrade() -> None:
    op.rename_table("transparencia", "transparencias")
    op.rename_table("galeria", "galerias")
    op.rename_table("textos", "textos_institucionais")
