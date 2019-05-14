"""add arrival, finish and reply times to ExpLatency

Revision ID: df219b111a5d
Revises: 5af9d0eb40e2
Create Date: 2019-05-14 16:33:33.201141

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'df219b111a5d'
down_revision = '5af9d0eb40e2'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('ExpLatency', sa.Column('arrival', sa.Integer))
    op.add_column('ExpLatency', sa.Column('finished', sa.Integer))
    op.add_column('ExpLatency', sa.Column('reply', sa.Integer))

def downgrade():
    op.drop_column('ExpLatency', 'arrival')
    op.drop_column('ExpLatency', 'finished')
    op.drop_column('ExpLatency', 'reply')
    
