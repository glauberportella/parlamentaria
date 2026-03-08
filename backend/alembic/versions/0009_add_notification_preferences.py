"""Add notification preference fields to eleitores.

New columns for engagement digest system:
- frequencia_notificacao: ENUM (IMEDIATA, DIARIA, SEMANAL, DESATIVADA)
  Default SEMANAL — new users get weekly digest by default.
- horario_preferido_notificacao: INTEGER (0-23), default 9.
- ultimo_digest_enviado: TIMESTAMP WITH TIMEZONE, nullable.

Revision ID: 0009
Revises: 0008
Create Date: 2026-03-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add notification preference columns to eleitores."""
    # Create FrequenciaNotificacao enum type
    freq_enum = sa.Enum(
        "IMEDIATA", "DIARIA", "SEMANAL", "DESATIVADA",
        name="frequencianotificacao",
    )
    freq_enum.create(op.get_bind(), checkfirst=True)

    # Add frequencia_notificacao column (default SEMANAL)
    op.add_column(
        "eleitores",
        sa.Column(
            "frequencia_notificacao",
            sa.Enum(
                "IMEDIATA", "DIARIA", "SEMANAL", "DESATIVADA",
                name="frequencianotificacao",
                create_type=False,
            ),
            server_default="SEMANAL",
            nullable=False,
        ),
    )

    # Add horario_preferido_notificacao (default 9 = 9h da manhã)
    op.add_column(
        "eleitores",
        sa.Column(
            "horario_preferido_notificacao",
            sa.Integer(),
            server_default="9",
            nullable=False,
        ),
    )

    # Add ultimo_digest_enviado (nullable, NULL = never sent)
    op.add_column(
        "eleitores",
        sa.Column(
            "ultimo_digest_enviado",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Remove notification preference columns from eleitores."""
    op.drop_column("eleitores", "ultimo_digest_enviado")
    op.drop_column("eleitores", "horario_preferido_notificacao")
    op.drop_column("eleitores", "frequencia_notificacao")

    # Drop the enum type
    sa.Enum(name="frequencianotificacao").drop(op.get_bind(), checkfirst=True)
