"""Initial revision

Revision ID: 4c75de87ac47
Revises:
Create Date: 2018-07-25 18:22:29.591826

"""
from alembic import context, op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4c75de87ac47'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # First data_file tables created before introducing db migration may exist
    # without an Alembic revision stamp; Alembic then starts with this revision,
    # and we must check that the table does not exist before creating it. Since
    # create_table() does not support CREATE TABLE IF NOT EXISTS, we check the
    # existence via SQLA.
    # noinspection PyProtectedMember
    engine = op._proxy.migration_context.connection.engine
    if not engine.dialect.has_table(engine, 'data_files'):
        op.create_table(
            'data_files',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('type', sa.String()),
            sa.Column('name', sa.String()),
            sa.Column('width', sa.Integer()),
            sa.Column('height', sa.Integer()),
            sa.Column('data_provider', sa.String()),
            sa.Column('asset_path', sa.String()),
            sa.Column('asset_metadata', sa.String()),
            sa.Column('layer', sa.String()),
            sa.Column('created_on', sa.DateTime(),
                      server_default=sa.func.now()),
        )


def downgrade():
    op.drop_table('data_files')
