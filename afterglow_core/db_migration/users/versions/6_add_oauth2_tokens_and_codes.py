"""Add OAuth2 tokens and codes"""
from alembic import op
import sqlalchemy as sa
import time

# revision identifiers, used by Alembic.
revision = '6'
down_revision = '5'
branch_labels = None
depends_on = None


def upgrade():
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
