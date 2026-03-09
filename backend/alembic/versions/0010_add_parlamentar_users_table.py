"""Add parlamentar_users table for dashboard authentication.

Creates the parlamentar_users table with:
- UUID primary key
- FK to deputados (optional)
- Email-based Magic Link authentication fields
- Invitation code support
- Refresh token hash for token rotation/revocation
- Custom enum tipo_parlamentar_user (DEPUTADO, ASSESSOR, LIDERANCA)

Revision ID: 0010
Revises: 0009
Create Date: 2026-03-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ARRAY


# revision identifiers, used by Alembic.
revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create parlamentar_users table and tipo_parlamentar_user enum."""
    # Create the enum type first (checkfirst avoids error if it already exists)
    tipo_enum = sa.Enum(
        "DEPUTADO", "ASSESSOR", "LIDERANCA",
        name="tipo_parlamentar_user",
        create_type=False,
    )
    tipo_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "parlamentar_users",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "deputado_id",
            sa.Integer(),
            sa.ForeignKey("deputados.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("email", sa.String(200), nullable=False, unique=True, index=True),
        sa.Column("nome", sa.String(300), nullable=False),
        sa.Column("cargo", sa.String(200), nullable=True),
        sa.Column(
            "tipo",
            tipo_enum,
            nullable=False,
            server_default="ASSESSOR",
        ),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("codigo_convite", sa.String(64), nullable=True, unique=True),
        sa.Column("convite_usado", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("ultimo_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column("temas_acompanhados", ARRAY(sa.String()), nullable=True),
        sa.Column("notificacoes_email", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("refresh_token_hash", sa.String(128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Drop parlamentar_users table and enum."""
    op.drop_table("parlamentar_users")
    sa.Enum(name="tipo_parlamentar_user").drop(op.get_bind(), checkfirst=True)
