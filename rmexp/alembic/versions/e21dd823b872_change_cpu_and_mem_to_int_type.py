"""change cpu and mem to int type

Revision ID: e21dd823b872
Revises: 77d5f6e59a44
Create Date: 2019-05-06 18:13:12.282664

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e21dd823b872'
down_revision = '77d5f6e59a44'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('ResourceLatency', 'cpu')
    op.drop_column('ResourceLatency', 'memory')
    op.add_column('ResourceLatency', sa.Column(
        'cpu', sa.Integer, nullable=False
    ))
    op.add_column('ResourceLatency', sa.Column(
        'memory', sa.Integer, nullable=False
    ))


def downgrade():
    op.add_column('ResourceLatency', sa.Column(
        'cpu', sa.Float
    ))
    op.add_column('ResourceLatency', sa.Column(
        'memory', sa.Float
    ))
