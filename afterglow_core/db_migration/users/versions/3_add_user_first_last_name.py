"""Add user settings"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3'
down_revision = '2'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table(
            'users', recreate='always',
            table_args=(
                sa.CheckConstraint(
                    'username is null or length(username) <= 255'),
                sa.CheckConstraint('email is null or length(email) <= 255'),
                sa.CheckConstraint(
                    'password is null or length(password) <= 255'),
                sa.CheckConstraint(
                    'first_name is null or length(first_name) <= 255'),
                sa.CheckConstraint(
                    'last_name is null or length(last_name) <= 255'),
                sa.CheckConstraint(
                    'auth_methods is null or length(auth_methods) <= 255'),
                sa.CheckConstraint(
                    'settings is null or length(settings) <= 1048576'),
            ),
            table_kwargs=dict(sqlite_autoincrement=True)) as batch_op:
        batch_op.add_column(sa.Column('first_name', sa.String, default=''))
        batch_op.add_column(sa.Column('last_name', sa.String, default=''))


def downgrade():
    with op.batch_alter_table('users', recreate='always') as batch_op:
        batch_op.drop_column('first_name')
        batch_op.drop_column('last_name')
