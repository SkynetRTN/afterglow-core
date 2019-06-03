"""Add user settings"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2'
down_revision = '1'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table(
            'users', recreate='always',
            table_kwargs=dict(sqlite_autoincrement=True)) as batch_op:
        batch_op.add_column(
            sa.Column('settings', sa.String(1 << 20), default=''))


def downgrade():
    with op.batch_alter_table('users', recreate='always') as batch_op:
        batch_op.drop_column('settings')
