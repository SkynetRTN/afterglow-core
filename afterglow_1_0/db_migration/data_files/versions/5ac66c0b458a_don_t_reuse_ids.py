"""Don't reuse IDs"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '5ac66c0b458a'
down_revision = '1'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table(
            'data_files', recreate='always',
            table_kwargs=dict(sqlite_autoincrement=True)):
        pass


def downgrade():
    with op.batch_alter_table('data_files', recreate='always'):
        pass
