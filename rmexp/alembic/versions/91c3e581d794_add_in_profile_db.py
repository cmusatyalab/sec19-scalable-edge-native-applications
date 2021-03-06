"""add in profile db

Revision ID: 91c3e581d794
Revises: e21dd823b872
Create Date: 2019-05-06 19:39:08.135402

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '91c3e581d794'
down_revision = 'e21dd823b872'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('Profile',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=512), nullable=False),
    sa.Column('trace', sa.String(length=512), nullable=False),
    sa.Column('index', sa.String(length=32), nullable=True),
    sa.Column('speed', sa.String(length=8192), nullable=True),
    sa.Column('data_length', sa.String(length=8192), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('Profile')
    # ### end Alembic commands ###
