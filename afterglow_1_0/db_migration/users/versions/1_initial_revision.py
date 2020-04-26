"""Initial revision"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # noinspection PyProtectedMember
    engine = op._proxy.migration_context.connection.engine

    if not engine.dialect.has_table(engine, 'users'):
        op.create_table(
            'roles',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('name', sa.String, unique=True),
            sa.Column('description', sa.String),
        )

    if not engine.dialect.has_table(engine, 'users'):
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

    if not engine.dialect.has_table(engine, 'user_roles'):
        op.create_table(
            'user_roles',
            sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id')),
            sa.Column('role_id', sa.Integer, sa.ForeignKey('roles.id')),
        )

    if not engine.dialect.has_table(engine, 'user_oauth_clients'):
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
