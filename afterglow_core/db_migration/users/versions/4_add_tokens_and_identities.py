"""Add persistent tokens, identities, and birth_date column"""
from alembic import op
import sqlalchemy as sa
import json

# revision identifiers, used by Alembic.
revision = '4'
down_revision = '3'
branch_labels = None
depends_on = None


def upgrade():
    identities_table = op.create_table(
        'identities',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column(
            'user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('auth_method', sa.String(), nullable=False),
        sa.Column('data', sa.Text(), default=''),
        sa.CheckConstraint('length(name) <= 255'),
        sa.CheckConstraint('length(auth_method) <= 40'),
        sqlite_autoincrement=True,
    )

    # Create an auth_method='skynet' Identity for each existing user
    # with User.auth_methods containing 'skynet'
    # noinspection SqlResolve
    users = op.execute(
        'select id, username, email, first_name, last_name, auth_methods '
        'from users').fetchall()
    identities = [
        dict(
            user_id=user[0],
            name=user[1] or user[2] or
            (user[3] or '' + ' ' + user[4] or '').strip() or str(user[0]),
            auth_method='skynet',
            data=json.dumps(dict(
                [('username', user[1])] +
                ([('email', user[2])] if user[2] else []) +
                ([('first_name', user[3])] if user[3] else []) +
                ([('last_name', user[4])] if user[4] else [])
            )),
        )
        for user in users if 'skynet' in user[5]
    ]
    op.bulk_insert(identities_table, identities)

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
        batch_op.drop_column('auth_methods')
        batch_op.add_column(sa.Column('birth_date', sa.Date))

    op.create_table(
        'tokens',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(
            'user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('token_type', sa.String(), default='personal'),
        sa.Column('access_token', sa.String(), unique=True, nullable=False),
        sa.Column('issued_at', sa.Integer()),
        sa.Column('expires_in', sa.Integer()),
        sa.Column('note', sa.Text(), default=''),
        sa.CheckConstraint('token_type is null or length(token_type) <= 40'),
        sa.CheckConstraint('length(access_token) <= 255'),
        sqlite_autoincrement=True,
    )


def downgrade():
    op.drop_table('tokens')

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
                        'settings is null or length(settings) <= 1048576'),
            ),
            table_kwargs=dict(sqlite_autoincrement=True)) as batch_op:
        batch_op.drop_column('birth_date')
        batch_op.add_column(
            sa.Column('auth_methods', sa.String, server_default=''))
        batch_op.add_constraint(
            sa.CheckConstraint(
                'auth_methods is null or length(auth_methods) <= 255'))

    # Set User.auth_methods='skynet_oauth' for all users having
    # Identity.auth_method='skynet'; use subquery since sqlite does not support
    # JOIN in UPDATE
    # noinspection SqlResolve
    op.execute(
        "update users set auth_methods = 'skynet_oauth' "
        "where id in (select user_id from identities "
        "where auth_method = 'skynet')")

    op.drop_table('identities')
