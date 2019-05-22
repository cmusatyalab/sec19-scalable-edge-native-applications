"""add in dutycycle gt

Revision ID: 9975c0e10837
Revises: 950cd7f3122a
Create Date: 2019-05-21 20:37:39.785501

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9975c0e10837'
down_revision = '950cd7f3122a'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('DutyCycleGT',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=512), nullable=False),
    sa.Column('trace', sa.String(length=512), nullable=False),
    sa.Column('index', sa.String(length=32), nullable=False),
    sa.Column('active', sa.String(length=32), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('DutyCycleGT')
    # ### end Alembic commands ###
