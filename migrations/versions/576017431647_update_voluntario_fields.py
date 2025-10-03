"""update voluntario fields

Revision ID: 576017431647
Revises: b9cf3df7f2f4
Create Date: 2025-10-03 17:09:17.391440

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '576017431647'
down_revision = 'b9cf3df7f2f4'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('voluntarios', schema=None) as batch_op:
        batch_op.add_column(sa.Column('area', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('descricao', sa.Text(), nullable=True))

    op.execute(
        "UPDATE voluntarios SET area = area_interesse, descricao = mensagem"
    )

    with op.batch_alter_table('voluntarios', schema=None) as batch_op:
        batch_op.drop_column('mensagem')
        batch_op.drop_column('area_interesse')
        batch_op.drop_column('telefone')
        batch_op.drop_column('email')


def downgrade():
    with op.batch_alter_table('voluntarios', schema=None) as batch_op:
        batch_op.add_column(sa.Column('email', sa.VARCHAR(length=255), nullable=True))
        batch_op.add_column(sa.Column('telefone', sa.VARCHAR(length=50), nullable=True))
        batch_op.add_column(sa.Column('area_interesse', sa.VARCHAR(length=255), nullable=True))
        batch_op.add_column(sa.Column('mensagem', sa.TEXT(), nullable=True))

    op.execute(
        "UPDATE voluntarios SET area_interesse = area, mensagem = descricao"
    )

    with op.batch_alter_table('voluntarios', schema=None) as batch_op:
        batch_op.drop_column('descricao')
        batch_op.drop_column('area')
