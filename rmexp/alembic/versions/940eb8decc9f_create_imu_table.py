"""create IMU table

Revision ID: 940eb8decc9f
Revises: 8fe434c4a08d
Create Date: 2019-04-21 13:30:06.238663

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '940eb8decc9f'
down_revision = '8fe434c4a08d'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'IMU',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(512), nullable=False),
        sa.Column('trace', sa.String(512), nullable=False),
        sa.Column('index', sa.String(32), nullable=False),
        sa.Column('sensor_timestamp', sa.DateTime()),
        sa.Column('rot_x', sa.Float),
        sa.Column('rot_y', sa.Float),
        sa.Column('rot_z', sa.Float),
        sa.Column('acc_x', sa.Float),
        sa.Column('acc_y', sa.Float),
        sa.Column('acc_z', sa.Float)
        )


def downgrade():
    op.drop_table('IMU')
