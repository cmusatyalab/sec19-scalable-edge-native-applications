"""add per frame utility to ExpLatency

Revision ID: 950cd7f3122a
Revises: be8dadc1ce2b
Create Date: 2019-05-18 20:56:25.497392

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '950cd7f3122a'
down_revision = 'be8dadc1ce2b'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('ExpLatency', sa.Column('utility', sa.Float))


def downgrade():
    op.drop_column('ExpLatency', 'utility')
