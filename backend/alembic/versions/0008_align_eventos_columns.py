"""Align eventos table columns with domain model.

Revision ID: 0008
Revises: 0007
Create Date: 2026-03-07

The domain model uses different column names than the initial migration:
  - data_hora_inicio → data_inicio
  - data_hora_fim → data_fim
  - tipo → tipo_evento
  - descricao: was nullable, now NOT NULL with default ''
  - add missing 'local' column (String 200, nullable)
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename columns to match domain model
    op.alter_column("eventos", "data_hora_inicio", new_column_name="data_inicio")
    op.alter_column("eventos", "data_hora_fim", new_column_name="data_fim")
    op.alter_column("eventos", "tipo", new_column_name="tipo_evento")

    # Make descricao NOT NULL with empty string default for existing rows
    op.execute("UPDATE eventos SET descricao = '' WHERE descricao IS NULL")
    op.alter_column(
        "eventos",
        "descricao",
        existing_type=sa.Text(),
        nullable=False,
        server_default="",
    )

    # Add missing 'local' column
    op.add_column("eventos", sa.Column("local", sa.String(200), nullable=True))


def downgrade() -> None:
    op.drop_column("eventos", "local")

    op.alter_column(
        "eventos",
        "descricao",
        existing_type=sa.Text(),
        nullable=True,
        server_default=None,
    )

    op.alter_column("eventos", "tipo_evento", new_column_name="tipo")
    op.alter_column("eventos", "data_fim", new_column_name="data_hora_fim")
    op.alter_column("eventos", "data_inicio", new_column_name="data_hora_inicio")
