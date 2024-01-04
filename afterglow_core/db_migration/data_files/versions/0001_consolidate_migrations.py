"""Consolidate all previous migrations"""
from datetime import datetime
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'sessions',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('user_id', sa.Integer(), index=True),
        sa.Column('name', sa.String(80), unique=True, nullable=False),
        sa.Column('data', sa.UnicodeText(1 << 31), nullable=True, server_default=''),
        sa.UniqueConstraint('user_id', 'name', name='_user_id_name_uc'),
    )

    op.create_table(
        'data_files',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('user_id', sa.Integer(), index=True),
        sa.Column('type', sa.String(255)),
        sa.Column('name', sa.String(1023)),
        sa.Column('width', sa.Integer()),
        sa.Column('height', sa.Integer()),
        sa.Column('data_provider', sa.String(255)),
        sa.Column('asset_path', sa.Text(16383)),
        sa.Column('asset_type', sa.String(255), server_default='FITS'),
        sa.Column('asset_metadata', sa.UnicodeText(1 << 31)),
        sa.Column('layer', sa.String(255)),
        sa.Column('created_on', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('modified', sa.Boolean(), server_default='0'),
        sa.Column('modified_on', sa.DateTime(), onupdate=datetime.utcnow),
        sa.Column(
            'session_id', sa.Integer(),
            sa.ForeignKey('sessions.id', name='fk_sessions_id', ondelete='cascade'),
            nullable=True, index=True),
        sa.Column('group_name', sa.String(1023), nullable=False, index=True),
        sa.Column('group_order', sa.Integer(), nullable=False, server_default='0'),
    )


def downgrade():
    op.drop_table('data_files')
    op.drop_table('sessions')
