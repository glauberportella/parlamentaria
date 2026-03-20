"""Add social_posts table for social media management.

Creates the social_posts table with:
- UUID primary key
- FKs to proposicoes and comparativos_votacao (optional)
- Post content, image data, status tracking
- Network-specific post IDs and metrics (likes/shares/comments/impressions)
- Three enums: rede_social, tipo_post_social, status_post
- Unique constraint to prevent duplicate posts

Revision ID: 0012
Revises: 0011
Create Date: 2026-03-15
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ENUM as PgEnum


# revision identifiers, used by Alembic.
revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create social_posts table and related enums."""
    # Create enums via raw SQL (safe against re-runs)
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE rede_social AS ENUM ("
        "'twitter', 'facebook', 'instagram', 'linkedin', 'discord', 'reddit'"
        "); "
        "EXCEPTION WHEN duplicate_object THEN null; "
        "END $$;"
    )
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE tipo_post_social AS ENUM ("
        "'resumo_semanal', 'votacao_relevante', 'comparativo', "
        "'destaque_proposicao', 'explicativo_educativo'"
        "); "
        "EXCEPTION WHEN duplicate_object THEN null; "
        "END $$;"
    )
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE status_post AS ENUM ("
        "'rascunho', 'aprovado', 'publicado', 'falhou', 'cancelado'"
        "); "
        "EXCEPTION WHEN duplicate_object THEN null; "
        "END $$;"
    )

    # Use PgEnum with create_type=False to avoid double create
    rede_enum = PgEnum(
        "twitter", "facebook", "instagram", "linkedin", "discord", "reddit",
        name="rede_social", create_type=False,
    )
    tipo_enum = PgEnum(
        "resumo_semanal", "votacao_relevante", "comparativo",
        "destaque_proposicao", "explicativo_educativo",
        name="tipo_post_social", create_type=False,
    )
    status_enum = PgEnum(
        "rascunho", "aprovado", "publicado", "falhou", "cancelado",
        name="status_post", create_type=False,
    )

    op.create_table(
        "social_posts",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("tipo", tipo_enum, nullable=False),
        sa.Column("rede", rede_enum, nullable=False),
        sa.Column("texto", sa.Text, nullable=False),
        sa.Column("imagem_url", sa.String(500), nullable=True),
        sa.Column("imagem_path", sa.String(500), nullable=True),
        sa.Column("status", status_enum, nullable=False, server_default="rascunho"),
        sa.Column("proposicao_id", sa.Integer, nullable=True),
        sa.Column("comparativo_id", UUID(as_uuid=False), nullable=True),
        sa.Column("rede_post_id", sa.String(200), nullable=True),
        sa.Column("publicado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("erro", sa.Text, nullable=True),
        sa.Column("likes", sa.Integer, nullable=False, server_default="0"),
        sa.Column("shares", sa.Integer, nullable=False, server_default="0"),
        sa.Column("comments", sa.Integer, nullable=False, server_default="0"),
        sa.Column("impressions", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # Foreign keys
        sa.ForeignKeyConstraint(
            ["proposicao_id"], ["proposicoes.id"],
            name="fk_social_posts_proposicao",
        ),
        sa.ForeignKeyConstraint(
            ["comparativo_id"], ["comparativos_votacao.id"],
            name="fk_social_posts_comparativo",
        ),
        # Unique constraint: one post per tipo+rede+proposicao+comparativo
        sa.UniqueConstraint(
            "tipo", "rede", "proposicao_id", "comparativo_id",
            name="uq_social_post_unique",
        ),
    )

    # Indexes for common queries
    op.create_index("ix_social_posts_status", "social_posts", ["status"])
    op.create_index("ix_social_posts_rede", "social_posts", ["rede"])
    op.create_index("ix_social_posts_tipo", "social_posts", ["tipo"])
    op.create_index("ix_social_posts_created_at", "social_posts", ["created_at"])
    op.create_index(
        "ix_social_posts_proposicao_id", "social_posts", ["proposicao_id"],
    )


def downgrade() -> None:
    """Drop social_posts table and enums."""
    op.drop_table("social_posts")

    op.execute("DROP TYPE IF EXISTS status_post")
    op.execute("DROP TYPE IF EXISTS tipo_post_social")
    op.execute("DROP TYPE IF EXISTS rede_social")
