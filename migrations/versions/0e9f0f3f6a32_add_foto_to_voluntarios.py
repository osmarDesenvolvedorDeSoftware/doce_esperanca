"""add foto to voluntarios

Revision ID: 0e9f0f3f6a32
Revises: 576017431647
Create Date: 2025-10-04 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0e9f0f3f6a32'
down_revision = '576017431647'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('voluntarios', schema=None) as batch_op:
        batch_op.add_column(sa.Column('foto', sa.String(length=512), nullable=True))


def downgrade():
    with op.batch_alter_table('voluntarios', schema=None) as batch_op:
        batch_op.drop_column('foto')
