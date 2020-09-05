"""Add field cals"""
from datetime import datetime
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5'
down_revision = '4'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'data_files', sa.Column('modified', sa.Boolean(), server_default='0'))
    op.add_column('data_files', sa.Column(
        'modified_on', sa.DateTime(), onupdate=datetime.utcnow))


def downgrade():
    op.drop_column('data_files', 'modified')
    op.drop_column('data_files', 'modified_on')
