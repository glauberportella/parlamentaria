"""Add export_jobs table for async export processing.

Creates the export_jobs table to track background CSV export jobs:
- PENDING → PROCESSING → COMPLETED/FAILED → EXPIRED
- Files stored in EXPORT_DIR, auto-cleaned after expiry

Revision ID: 0014
Revises: 0013
Create Date: 2026-03-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "export_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "parlamentar_user_id",
            UUID(as_uuid=False),
            sa.ForeignKey("parlamentar_users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("filtros", JSONB, nullable=True),
        sa.Column("total_rows", sa.Integer, nullable=True),
        sa.Column("file_name", sa.String(255), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "notificado_email",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Index for cleanup query (find expired completed jobs)
    op.create_index(
        "ix_export_jobs_status_expires",
        "export_jobs",
        ["status", "expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_export_jobs_status_expires", table_name="export_jobs")
    op.drop_table("export_jobs")
