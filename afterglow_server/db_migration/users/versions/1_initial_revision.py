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
            sa.Column('id', sa.Integer(), primary_key=True),
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


def downgrade():
    pass
