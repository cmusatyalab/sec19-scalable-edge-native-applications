"""add in sec6 table

Revision ID: 84234e01c344
Revises: 9975c0e10837
Create Date: 2019-05-22 10:02:50.202705

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '84234e01c344'
down_revision = '9975c0e10837'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('Sec6IntraApp',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=512), nullable=False),
    sa.Column('index', sa.Integer(), nullable=True),
    sa.Column('app', sa.String(length=32), nullable=True),
    sa.Column('client', sa.String(length=32), nullable=True),
    sa.Column('arrival', sa.Integer(), nullable=True),
    sa.Column('finished', sa.Integer(), nullable=True),
    sa.Column('reply', sa.Integer(), nullable=True),
    sa.Column('utility', sa.Float(), nullable=True),
    sa.Column('processed', sa.Integer(), nullable=True),
    sa.Column('result', sa.String(length=512), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('Sec6IntraApp')
    # ### end Alembic commands ###
