"""add in gtinst2

Revision ID: 7626e7530ece
Revises: b6abe28f794b
Create Date: 2019-05-23 19:46:56.910109

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7626e7530ece'
down_revision = 'b6abe28f794b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('GTInst',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('app', sa.String(length=512), nullable=False),
                    sa.Column('trace', sa.String(length=512), nullable=False),
                    sa.Column('value', sa.String(length=16384), nullable=True),
                    sa.PrimaryKeyConstraint('id')
                    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('GTInst')
    # ### end Alembic commands ###
