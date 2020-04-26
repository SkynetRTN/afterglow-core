"""Add field cals"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4'
down_revision = '3'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'field_cals',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('name', sa.String(), unique=True, nullable=False, index=True),
        sa.Column('catalog_sources', sa.String()),
        sa.Column('catalogs', sa.String()),
        sa.Column('custom_filter_lookup', sa.String()),
        sa.Column('source_inclusion_percent', sa.Float()),
        sa.Column('min_snr', sa.Float(), server_default='0'),
        sa.Column('max_snr', sa.Float(), server_default='0'),
        sa.Column('source_match_tol', sa.Float()),
        sqlite_autoincrement=True,
    )

    with op.batch_alter_table(
            'field_cals',
            table_args=(sa.CheckConstraint('length(name) <= 1024'),),
            table_kwargs=dict(sqlite_autoincrement=True)):
        pass


def downgrade():
    op.drop_table('field_cals')
