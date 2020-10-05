"""Add file groups"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6'
down_revision = '5'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('data_files', sa.Column(
        'group_id', sa.String(), nullable=True, index=True))
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
                sa.CheckConstraint('length(group_id) = 36'),
            ),
            table_kwargs=dict(sqlite_autoincrement=True)) as batch_op:
        batch_op.alter_column('group_id', nullable=False)
        batch_op.add_column(sa.Column(
            'group_order', sa.Integer(), nullable=False, server_default='0'))


def downgrade():
    op.drop_index('ik_group_id', 'data_files')
    op.drop_column('data_files', 'group_id')
    op.drop_column('data_files', 'group_order')
