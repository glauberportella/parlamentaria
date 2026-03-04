"""Add eleitor eligibility fields and voto tipo_voto classification.

New columns:
- eleitores.data_nascimento (DATE, nullable)
- eleitores.cidadao_brasileiro (BOOLEAN, default false)
- votos_populares.tipo_voto (ENUM TipoVoto, default 'OPINIAO')

Existing votes are backfilled as OPINIAO since we cannot retroactively
determine the voter's eligibility at the time of the original vote.
They can be reclassified later if the voter completes their profile.

Revision ID: 0003_add_eligibility
Revises: 0002_add_pgvector_rag
Create Date: 2026-03-03 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003_add_eligibility"
down_revision: Union[str, None] = "0002_add_pgvector_rag"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add eligibility fields to eleitores and tipo_voto to votos_populares."""
    # --- Eleitor: new columns ---
    op.add_column(
        "eleitores",
        sa.Column("data_nascimento", sa.Date(), nullable=True),
    )
    op.add_column(
        "eleitores",
        sa.Column(
            "cidadao_brasileiro",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # --- VotoPopular: tipo_voto enum + column ---
    # Create the enum type first
    tipo_voto_enum = sa.Enum("OFICIAL", "OPINIAO", name="tipovoto")
    tipo_voto_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "votos_populares",
        sa.Column(
            "tipo_voto",
            tipo_voto_enum,
            nullable=False,
            server_default="OPINIAO",
        ),
    )

    # Create index for efficient filtering by tipo_voto in consolidation queries
    op.create_index(
        "ix_votos_populares_tipo_voto",
        "votos_populares",
        ["tipo_voto"],
    )
    op.create_index(
        "ix_votos_populares_proposicao_tipo",
        "votos_populares",
        ["proposicao_id", "tipo_voto"],
    )


def downgrade() -> None:
    """Remove eligibility fields and tipo_voto."""
    op.drop_index("ix_votos_populares_proposicao_tipo", table_name="votos_populares")
    op.drop_index("ix_votos_populares_tipo_voto", table_name="votos_populares")
    op.drop_column("votos_populares", "tipo_voto")

    # Drop the enum type
    sa.Enum(name="tipovoto").drop(op.get_bind(), checkfirst=True)

    op.drop_column("eleitores", "cidadao_brasileiro")
    op.drop_column("eleitores", "data_nascimento")
