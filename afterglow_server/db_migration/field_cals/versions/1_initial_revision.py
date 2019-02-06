"""Initial revision"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'field_cals',
        sa.Column('name', sa.String(), primary_key=True, nullable=False),
        sa.Column('catalog_sources', sa.String()),
        sa.Column('catalogs', sa.String()),
        sa.Column('custom_filter_lookup', sa.String()),
        sa.Column('source_inclusion_percent', sa.Float()),
        sa.Column('min_snr', sa.Float(), server_default='0'),
        sa.Column('max_snr', sa.Float(), server_default='0'),
        sa.Column('source_match_tol', sa.Float()),
    )


def downgrade():
    op.drop_table('data_files')
