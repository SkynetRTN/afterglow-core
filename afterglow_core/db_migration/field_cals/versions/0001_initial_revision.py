"""Initial revision"""
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
        'field_cals',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('user_id', sa.Integer(), index=True),
        sa.Column('name', sa.String(1023), nullable=False, index=True),
        sa.Column('catalog_sources', sa.UnicodeText(1 << 31)),
        sa.Column('catalogs', sa.UnicodeText(1 << 31)),
        sa.Column('custom_filter_lookup', sa.UnicodeText(1 << 31)),
        sa.Column('source_inclusion_percent', sa.Float()),
        sa.Column('min_snr', sa.Float(), server_default='0'),
        sa.Column('max_snr', sa.Float(), server_default='0'),
        sa.Column('source_match_tol', sa.Float()),
        sa.Column('variable_check_tol', sa.Float(), server_default='5'),
        sa.Column('max_star_rms', sa.Float(), server_default='0'),
        sa.Column('max_stars', sa.Integer(), server_default='0'),
        sa.UniqueConstraint('user_id', 'name', name='_user_id_name_uc'),
    )


def downgrade():
    op.drop_table('field_cals')
