"""Track data file modification"""
from datetime import datetime
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5'
down_revision = '4'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table(
            'data_files',
            table_args=(
                    sa.CheckConstraint('length(name) <= 1024'),
                    sa.CheckConstraint('length(group_id) = 36'),
            ),
            table_kwargs=dict(sqlite_autoincrement=True)) as batch_op:
        batch_op.add_column(sa.Column(
            'modified', sa.Boolean(), server_default='0'))
        batch_op.add_column(sa.Column(
            'modified_on', sa.DateTime(), onupdate=datetime.utcnow))


def downgrade():
    with op.batch_alter_table(
            'data_files',
            table_args=(
                    sa.CheckConstraint('length(name) <= 1024'),
                    sa.CheckConstraint('length(group_id) = 36'),
            ),
            table_kwargs=dict(sqlite_autoincrement=True)) as batch_op:
        batch_op.drop_column('modified')
        batch_op.drop_column('modified_on')
