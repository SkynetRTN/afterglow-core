"""Add sessions"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3'
down_revision = '5ac66c0b458a'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'sessions',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('name', sa.String, unique=True, nullable=False),
        sa.Column('data', sa.String, nullable=True, server_default=''),
        sa.CheckConstraint('length(name) <= 80'),
        sa.CheckConstraint('data is null or length(data) <= 1048576'),
        sqlite_autoincrement=True,
    )

    with op.batch_alter_table(
            'data_files',
            table_args=(sa.CheckConstraint('length(name) <= 1024'),),
            table_kwargs=dict(sqlite_autoincrement=True)) as batch_op:
        batch_op.add_column(sa.Column(
            'session_id', sa.Integer(),
            sa.ForeignKey('sessions.id', name='fk_sessions_id',
                          ondelete='cascade'), nullable=True, index=True))


def downgrade():
    with op.batch_alter_table(
            'data_files',
            table_kwargs=dict(sqlite_autoincrement=True)) as batch_op:
        batch_op.drop_column('session_id')

    op.drop_table('sessions')
