"""Add user settings"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4'
down_revision = '3'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'tokens',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(
            'user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('token_type', sa.String(), default='personal'),
        sa.Column('access_token', sa.String(), unique=True, nullable=False),
        sa.Column('issued_at', sa.Integer()),
        sa.Column('expires_in', sa.Integer()),
        sa.Column('note', sa.Text(), default=''),
        sa.CheckConstraint('token_type is null or length(token_type) <= 40'),
        sa.CheckConstraint('length(access_token) <= 255'),
        sqlite_autoincrement=True,
    )


def downgrade():
    op.drop_table('tokens')
