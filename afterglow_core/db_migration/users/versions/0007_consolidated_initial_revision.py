"""Initial revision consolidating previous revisions 1 to 6"""

import time

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0007'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String, unique=True),
        sa.Column('description', sa.String),
        sa.CheckConstraint('length(name) <= 80'),
        sa.CheckConstraint(
            'description is null or length(description) <= 255'),
    )

    op.create_table(
        'users',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('username', sa.String, unique=True),
        sa.Column('email', sa.String),
        sa.Column('password', sa.String),
        sa.Column('first_name', sa.String, default=''),
        sa.Column('last_name', sa.String, default=''),
        sa.Column('active', sa.Boolean, server_default='1'),
        sa.Column(
            'created_at', sa.DateTime, default=sa.func.current_timestamp()),
        sa.Column(
            'modified_at', sa.DateTime, default=sa.func.current_timestamp(),
            onupdate=sa.func.current_timestamp()),
        sa.Column('settings', sa.String, default=''),
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
        sqlite_autoincrement=True,
    )

    op.create_table(
        'user_roles',
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id')),
        sa.Column('role_id', sa.Integer, sa.ForeignKey('roles.id')),
    )

    op.create_table(
        'user_oauth_clients',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column(
            'user_id', sa.Integer,
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False, index=True),
        sa.Column('client_id', sa.String, nullable=False, index=True),
        sa.CheckConstraint('length(client_id) <= 40'),
    )

    op.create_table(
        'identities',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column(
            'user_id', sa.Integer(), sa.ForeignKey('users.id'),
            nullable=False),
        sa.Column('auth_method', sa.String(), nullable=False),
        sa.Column('data', sa.Text(), default=''),
        sa.CheckConstraint('length(name) <= 255'),
        sa.CheckConstraint('length(auth_method) <= 40'),
        sqlite_autoincrement=True,
    )

    op.create_table(
        'tokens',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(
            'user_id', sa.Integer(), sa.ForeignKey('users.id'),
            nullable=False),
        sa.Column('token_type', sa.String(), default='personal'),
        sa.Column('access_token', sa.String(), unique=True, nullable=False),
        sa.Column('issued_at', sa.Integer()),
        sa.Column('expires_in', sa.Integer()),
        sa.Column('note', sa.Text(), default=''),
        sa.CheckConstraint('token_type is null or length(token_type) <= 40'),
        sa.CheckConstraint('length(access_token) <= 255'),
        sqlite_autoincrement=True,
    )

    op.create_table(
        'oauth_codes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(
            'user_id', sa.Integer(),
            sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('code', sa.String(), unique=True, nullable=False),
        sa.Column('client_id', sa.String()),
        sa.Column('redirect_uri', sa.Text(), default=''),
        sa.Column('response_type', sa.Text(), default=''),
        sa.Column('scope', sa.Text(), default=''),
        sa.Column('nonce', sa.Text()),
        sa.Column(
            'auth_time', sa.Integer(), nullable=False,
            default=lambda: int(time.time())
        ),
        sa.Column('code_challenge', sa.Text()),
        sa.Column('code_challenge_method', sa.String()),
        sa.CheckConstraint('length(code) <= 120'),
        sa.CheckConstraint('client_id is null or length(client_id) <= 48'),
        sa.CheckConstraint(
            'code_challenge_method is null or length(code_challenge_method) '
            '<= 48'),
        sqlite_autoincrement=True,
    )

    op.create_table(
        'oauth_tokens',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(
            'user_id', sa.Integer(),
            sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_type', sa.String(), default='oauth2'),
        sa.Column('note', sa.Text(), default=''),
        sa.Column('client_id', sa.String()),
        sa.Column('access_token', sa.String(), unique=True, nullable=False),
        sa.Column('refresh_token', sa.String(), index=True),
        sa.Column('scope', sa.Text(), default=''),
        sa.Column('revoked', sa.Boolean(), default=False),
        sa.Column(
            'issued_at', sa.Integer(), nullable=False,
            default=lambda: int(time.time())
        ),
        sa.Column('expires_in', sa.Integer(), nullable=False, default=0),
        sa.CheckConstraint('token_type is null or length(token_type) <= 40'),
        sa.CheckConstraint('client_id is null or length(client_id) <= 48'),
        sa.CheckConstraint('length(access_token) <= 255'),
        sa.CheckConstraint(
            'refresh_token is null or length(refresh_token) <= 255'),
        sqlite_autoincrement=True,
    )


def downgrade():
    op.drop_table('oauth_tokens')
    op.drop_table('oauth_codes')
    op.drop_table('tokens')
    op.drop_table('identities')
    op.drop_table('user_oauth_clients')
    op.drop_table('user_roles')
    op.drop_table('users')
    op.drop_table('roles')
