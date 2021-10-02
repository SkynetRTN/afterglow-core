"""Port to Alembic v1.6+, use the new versioning

WARNING. This migration must run with an Alembic version earlier than 1.6,
otherwise it will fail.
"""

# revision identifiers, used by Alembic.
revision = '0008'
down_revision = '7'
branch_labels = None
depends_on = None


def upgrade():
    # Do nothing, just change revision number
    pass


def downgrade():
    pass
