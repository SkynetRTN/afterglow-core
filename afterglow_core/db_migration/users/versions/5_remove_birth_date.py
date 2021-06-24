"""Remove birth_date column"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '5'
down_revision = '4'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table(
            'users', recreate='always',
            table_args=(
                    sa.CheckConstraint(
                        'username is null or length(username) <= 255'),
                    sa.CheckConstraint(
                        'password is null or length(password) <= 255'),
                    sa.CheckConstraint('email is null or length(email) <= 255'),
                    sa.CheckConstraint(
                        'first_name is null or length(first_name) <= 255'),
                    sa.CheckConstraint(
                        'last_name is null or length(last_name) <= 255'),
                    sa.CheckConstraint(
                        'settings is null or length(settings) <= 1048576'),
            ),
            table_kwargs=dict(sqlite_autoincrement=True)) as batch_op:
        batch_op.drop_column('birth_date')


def downgrade():
    with op.batch_alter_table(
            'users', recreate='always',
            table_args=(
                    sa.CheckConstraint(
                        'username is null or length(username) <= 255'),
                    sa.CheckConstraint(
                        'password is null or length(password) <= 255'),
                    sa.CheckConstraint('email is null or length(email) <= 255'),
                    sa.CheckConstraint(
                        'first_name is null or length(first_name) <= 255'),
                    sa.CheckConstraint(
                        'last_name is null or length(last_name) <= 255'),
                    sa.CheckConstraint(
                        'settings is null or length(settings) <= 1048576'),
            ),
            table_kwargs=dict(sqlite_autoincrement=True)) as batch_op:
        batch_op.add_column(sa.Column('birth_date', sa.Date))
