"""Don't reuse IDs

Revision ID: 5ac66c0b458a
Revises: 4c75de87ac47
Create Date: 2018-07-25 18:38:54.515858

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '5ac66c0b458a'
down_revision = '4c75de87ac47'
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
