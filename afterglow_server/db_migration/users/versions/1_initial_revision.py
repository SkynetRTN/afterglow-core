"""Initial revision"""
from alembic import context, op
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
            sa.Column('name', sa.String(80), unique=True),
            sa.Column('description', sa.String(255)),
        )

    if not engine.dialect.has_table(engine, 'users'):
        op.create_table(
            'users',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('username', sa.String(255), unique=True),
            sa.Column('email', sa.String(255)),
            sa.Column('password', sa.String(255)),
            sa.Column('active', sa.Boolean, server_default='1'),
            sa.Column(
                'created_at', sa.DateTime, default=sa.func.current_timestamp()),
            sa.Column(
                'modified_at', sa.DateTime, default=sa.func.current_timestamp(),
                onupdate=sa.func.current_timestamp()),
            sa.Column('auth_methods', sa.String(255), server_default=''),
        )


def downgrade():
    pass
