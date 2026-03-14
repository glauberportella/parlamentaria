"""Add is_admin column to parlamentar_users table.

Enables admin functionality in the parliamentary dashboard:
users with is_admin=True can manage invitations and other users.

Revision ID: 0011
Revises: 0010
Create Date: 2026-03-14
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "parlamentar_users",
        sa.Column(
            "is_admin",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("parlamentar_users", "is_admin")
