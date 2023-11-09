"""Change oauth_tokens.revoked to access_token_revoked_at +
refresh_token_revoked_at"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table(
            'oauth_tokens',
            table_args=(
                sa.CheckConstraint('token_type is null or length(token_type) <= 40'),
                sa.CheckConstraint('client_id is null or length(client_id) <= 48'),
                sa.CheckConstraint('length(access_token) <= 255'),
                sa.CheckConstraint('refresh_token is null or length(refresh_token) <= 255'),
            )) as batch_op:
        batch_op.drop_column('revoked')
        batch_op.add_column(sa.Column('access_token_revoked_at', sa.Integer, nullable=False, default=0))
        batch_op.add_column(sa.Column('refresh_token_revoked_at', sa.Integer, nullable=False, default=0))


def downgrade():
    with op.batch_alter_table(
            'oauth_tokens',
            table_args=(
                sa.CheckConstraint('token_type is null or length(token_type) <= 40'),
                sa.CheckConstraint('client_id is null or length(client_id) <= 48'),
                sa.CheckConstraint('length(access_token) <= 255'),
                sa.CheckConstraint('refresh_token is null or length(refresh_token) <= 255'),
            )) as batch_op:
        batch_op.drop_column('access_token_revoked_at')
        batch_op.drop_column('refresh_token_revoked_at')
        batch_op.add_column(sa.Column('revoked', sa.Boolean(), default=False))
