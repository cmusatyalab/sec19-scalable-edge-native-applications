"""Add app name to ExpLatency

Revision ID: d741ee0ea4a9
Revises: b1b34d862ddd
Create Date: 2019-05-12 21:11:27.877331

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd741ee0ea4a9'
down_revision = 'b1b34d862ddd'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('ExpLatency', sa.Column('app', sa.String(length=32), nullable=True))


def downgrade():
    op.drop_column('ExpLatency', 'app')

