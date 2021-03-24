"""Initial revision"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    tables = sa.inspect(op.get_bind()).get_table_names()

    if 'roles' not in tables:
        op.create_table(
            'roles',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('name', sa.String, unique=True),
            sa.Column('description', sa.String),
        )

    if 'users' not in tables:
        op.create_table(
            'users',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('username', sa.String, unique=True),
            sa.Column('email', sa.String),
            sa.Column('password', sa.String),
            sa.Column('active', sa.Boolean, server_default='1'),
            sa.Column(
                'created_at', sa.DateTime, default=sa.func.current_timestamp()),
            sa.Column(
                'modified_at', sa.DateTime, default=sa.func.current_timestamp(),
                onupdate=sa.func.current_timestamp()),
            sa.Column('auth_methods', sa.String, server_default=''),
        )

    if 'user_roles' not in tables:
        op.create_table(
            'user_roles',
            sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id')),
            sa.Column('role_id', sa.Integer, sa.ForeignKey('roles.id')),
        )

    if 'user_oauth_clients' not in tables:
        op.create_table(
            'user_oauth_clients',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column(
                'user_id', sa.Integer,
                sa.ForeignKey('users.id', ondelete='CASCADE'),
                nullable=False, index=True),
            sa.Column('client_id', sa.String, nullable=False, index=True),
        )


def downgrade():
    pass
