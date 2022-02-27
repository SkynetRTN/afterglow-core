"""Track data file modification"""
from datetime import datetime
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table(
            'field_cals',
            table_args=(sa.CheckConstraint('length(name) <= 1024'),),
            table_kwargs=dict(sqlite_autoincrement=True)) as batch_op:
        batch_op.add_column(sa.Column(
            'variable_check_tol', sa.Float(), server_default='5'))
        batch_op.add_column(sa.Column(
            'max_star_rms', sa.Float(), server_default='0'))
        batch_op.add_column(sa.Column(
            'max_stars', sa.Integer(), server_default='0'))


def downgrade():
    with op.batch_alter_table(
            'field_cals',
            table_args=(sa.CheckConstraint('length(name) <= 1024'),),
            table_kwargs=dict(sqlite_autoincrement=True)) as batch_op:
        batch_op.drop_column('variable_check_tol')
        batch_op.drop_column('max_star_rms')
        batch_op.drop_column('max_stars')
