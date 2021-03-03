"""Rename group_id to group_name; add asset_type"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7'
down_revision = '6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table(
            'data_files',
            table_args=(
                sa.CheckConstraint('length(name) <= 1024'),
                sa.CheckConstraint('length(group_name) <= 1024')),
            table_kwargs=dict(sqlite_autoincrement=True)) as batch_op:
        batch_op.drop_index('ix_data_files_group_id')
        batch_op.alter_column('group_id', new_column_name='group_name')
        batch_op.add_column(sa.Column(
            'asset_type', sa.String, server_default='FITS'))

    # noinspection SqlResolve
    op.execute('update data_files set group_name = coalesce(name, id)')

    with op.batch_alter_table(
            'data_files',
            table_args=(
                sa.CheckConstraint('length(name) <= 1024'),
                sa.CheckConstraint('length(group_name) <= 1024')),
            table_kwargs=dict(sqlite_autoincrement=True)) as batch_op:
        batch_op.create_index('ix_data_files_group_name', ['group_name'])


def downgrade():
    with op.batch_alter_table(
            'data_files',
            table_args=(sa.CheckConstraint('length(name) <= 1024'),),
            table_kwargs=dict(sqlite_autoincrement=True)) as batch_op:
        batch_op.drop_column('asset_type')
        batch_op.drop_index('ix_data_files_group_name')
        batch_op.alter_column('group_name', new_column_name='group_id')

    # noinspection SqlResolve
    op.execute(
        "update data_files "
        "set group_id = lower(hex(randomblob(4))) || '-' || "
        "lower(hex(randomblob(2))) || '-4' || "
        "substr(lower(hex(randomblob(2))),2) || '-' || "
        "substr('89ab',abs(random()) % 4 + 1, 1) || "
        "substr(lower(hex(randomblob(2))),2) || '-' || "
        "lower(hex(randomblob(6)))")

    with op.batch_alter_table(
            'data_files',
            table_args=(
                sa.CheckConstraint('length(name) <= 1024'),
                sa.CheckConstraint('length(group_id) = 36')),
            table_kwargs=dict(sqlite_autoincrement=True)) as batch_op:
        batch_op.create_index('ix_data_files_group_id', ['group_id'])
