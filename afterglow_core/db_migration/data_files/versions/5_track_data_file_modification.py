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
    with op.batch_alter_table(
            'data_files',
            table_args=(sa.CheckConstraint('length(name) <= 1024'),),
            table_kwargs=dict(sqlite_autoincrement=True)) as batch_op:
        batch_op.add_column(sa.Column('modified', sa.Boolean(), default=False))
        batch_op.add_column(sa.Column(
            'modified_on', sa.DateTime(),
            default=lambda ctx: ctx.get_current_parameters()['created_on'],
            onupdate=datetime.utcnow))


def downgrade():
    with op.batch_alter_table(
            'data_files',
            table_args=(sa.CheckConstraint('length(name) <= 1024'),),
            table_kwargs=dict(sqlite_autoincrement=True)) as batch_op:
        batch_op.drop_column('modified')
        batch_op.drop_column('modified_on')
