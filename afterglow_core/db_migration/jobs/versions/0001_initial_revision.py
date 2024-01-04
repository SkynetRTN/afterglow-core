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
        'jobs',
        sa.Column('id', sa.String(36), primary_key=True, nullable=False),
        sa.Column('type', sa.String(40), nullable=False, index=True),
        sa.Column('user_id', sa.Integer, index=True),
        sa.Column('session_id', sa.Integer, nullable=True, index=True),
        sa.Column('args', sa.UnicodeText(1 << 31)),
    )

    op.create_table(
        'job_states',
        sa.Column('id', sa.String(36), sa.ForeignKey('jobs.id', ondelete='CASCADE'), index=True, primary_key=True),
        sa.Column('status', sa.String(16), nullable=False, index=True, default='pending'),
        sa.Column('created_on', sa.DateTime, nullable=False),
        sa.Column('started_on', sa.DateTime, index=True),
        sa.Column('completed_on', sa.DateTime),
        sa.Column('progress', sa.Float, nullable=False, default=0, index=True),
    )


def downgrade():
    op.drop_table('job_states')
    op.drop_table('jobs')
