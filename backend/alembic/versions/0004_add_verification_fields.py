"""Add identity verification fields to eleitores.

New columns:
- eleitores.cpf_hash (VARCHAR(64), unique, nullable)
- eleitores.titulo_eleitor_hash (VARCHAR(64), unique, nullable)
- eleitores.nivel_verificacao (ENUM NivelVerificacao, default 'NAO_VERIFICADO')

Existing eleitores are backfilled:
- nivel_verificacao = NAO_VERIFICADO (default)
- cpf_hash / titulo_eleitor_hash = NULL

Revision ID: 0004_add_verification
Revises: 0003_add_eligibility
Create Date: 2026-03-04 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0004_add_verification"
down_revision: Union[str, None] = "0003_add_eligibility"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add verification fields to eleitores."""
    # --- Create NivelVerificacao enum ---
    nivel_enum = sa.Enum(
        "NAO_VERIFICADO", "AUTO_DECLARADO", "VERIFICADO_TITULO",
        name="nivelverificacao",
    )
    nivel_enum.create(op.get_bind(), checkfirst=True)

    # --- Eleitores: new columns ---
    op.add_column(
        "eleitores",
        sa.Column("cpf_hash", sa.String(64), nullable=True, unique=True),
    )
    op.add_column(
        "eleitores",
        sa.Column("titulo_eleitor_hash", sa.String(64), nullable=True, unique=True),
    )
    op.add_column(
        "eleitores",
        sa.Column(
            "nivel_verificacao",
            nivel_enum,
            nullable=False,
            server_default="NAO_VERIFICADO",
        ),
    )

    # Indexes for hash lookups
    op.create_index(
        "ix_eleitores_cpf_hash",
        "eleitores",
        ["cpf_hash"],
        unique=True,
    )
    op.create_index(
        "ix_eleitores_titulo_eleitor_hash",
        "eleitores",
        ["titulo_eleitor_hash"],
        unique=True,
    )
    op.create_index(
        "ix_eleitores_nivel_verificacao",
        "eleitores",
        ["nivel_verificacao"],
    )


def downgrade() -> None:
    """Remove verification fields."""
    op.drop_index("ix_eleitores_nivel_verificacao", table_name="eleitores")
    op.drop_index("ix_eleitores_titulo_eleitor_hash", table_name="eleitores")
    op.drop_index("ix_eleitores_cpf_hash", table_name="eleitores")
    op.drop_column("eleitores", "nivel_verificacao")
    op.drop_column("eleitores", "titulo_eleitor_hash")
    op.drop_column("eleitores", "cpf_hash")

    # Drop the enum type
    sa.Enum(name="nivelverificacao").drop(op.get_bind(), checkfirst=True)
