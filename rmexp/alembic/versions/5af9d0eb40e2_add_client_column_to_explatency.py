"""Add client column to ExpLatency

Revision ID: 5af9d0eb40e2
Revises: 302b491278ce
Create Date: 2019-05-14 13:57:21.184017

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5af9d0eb40e2'
down_revision = '302b491278ce'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('ExpLatency', sa.Column('client', sa.String(length=32), nullable=True))


def downgrade():
    op.drop_column('ExpLatency', 'client')
