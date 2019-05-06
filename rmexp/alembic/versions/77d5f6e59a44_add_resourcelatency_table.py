"""add ResourceLatency table

Revision ID: 77d5f6e59a44
Revises: 5215cd02948d
Create Date: 2019-05-06 18:02:43.485807

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '77d5f6e59a44'
down_revision = '5215cd02948d'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'ResourceLatency',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('trace', sa.String(512), nullable=False),
        sa.Column('index', sa.String(32), nullable=False),
        sa.Column('cpu', sa.Float),
        sa.Column('memory', sa.Float),
        sa.Column('latency', sa.Float),
    )


def downgrade():
    op.drop_table('ResourceLatency')
