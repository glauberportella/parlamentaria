"""Initial schema — all domain models.

Revision ID: 0001_initial
Revises: None
Create Date: 2024-01-01 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables."""
    # proposicoes
    op.create_table(
        "proposicoes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("ano", sa.Integer(), nullable=False),
        sa.Column("ementa", sa.Text(), nullable=False),
        sa.Column("texto_completo_url", sa.String(500), nullable=True),
        sa.Column("data_apresentacao", sa.Date(), nullable=False),
        sa.Column("situacao", sa.String(200), nullable=False, server_default="Em tramitação"),
        sa.Column("temas", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("autores", postgresql.JSONB(), nullable=True),
        sa.Column("resumo_ia", sa.Text(), nullable=True),
        sa.Column("ultima_sincronizacao", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # votacoes
    op.create_table(
        "votacoes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("proposicao_id", sa.Integer(), nullable=True),
        sa.Column("data", sa.DateTime(timezone=True), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("aprovacao", sa.Boolean(), nullable=True),
        sa.Column("votos_sim", sa.Integer(), server_default="0"),
        sa.Column("votos_nao", sa.Integer(), server_default="0"),
        sa.Column("abstencoes", sa.Integer(), server_default="0"),
        sa.Column("orientacoes", postgresql.JSONB(), nullable=True),
        sa.Column("votos_parlamentares", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["proposicao_id"], ["proposicoes.id"]),
    )

    # deputados
    op.create_table(
        "deputados",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("nome_civil", sa.String(300), nullable=True),
        sa.Column("sigla_partido", sa.String(20), nullable=True),
        sa.Column("sigla_uf", sa.String(2), nullable=True),
        sa.Column("foto_url", sa.String(500), nullable=True),
        sa.Column("email", sa.String(200), nullable=True),
        sa.Column("situacao", sa.String(100), nullable=True),
        sa.Column("dados_extras", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # partidos
    op.create_table(
        "partidos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sigla", sa.String(20), nullable=False),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sigla", name="uq_partido_sigla"),
    )

    # eleitores
    op.create_table(
        "eleitores",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("email", sa.String(300), nullable=False),
        sa.Column("uf", sa.String(2), nullable=False),
        sa.Column("chat_id", sa.String(100), nullable=True),
        sa.Column("channel", sa.String(20), server_default="telegram"),
        sa.Column("verificado", sa.Boolean(), server_default="false"),
        sa.Column("temas_interesse", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("data_cadastro", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_eleitor_email"),
        sa.UniqueConstraint("chat_id", name="uq_eleitor_chat_id"),
    )

    # votos_populares
    op.create_table(
        "votos_populares",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("eleitor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("proposicao_id", sa.Integer(), nullable=False),
        sa.Column("voto", sa.Enum("SIM", "NAO", "ABSTENCAO", name="votoenum"), nullable=False),
        sa.Column("justificativa", sa.Text(), nullable=True),
        sa.Column("data_voto", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["eleitor_id"], ["eleitores.id"]),
        sa.ForeignKeyConstraint(["proposicao_id"], ["proposicoes.id"]),
        sa.UniqueConstraint("eleitor_id", "proposicao_id", name="uq_eleitor_proposicao"),
    )

    # analises_ia
    op.create_table(
        "analises_ia",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("proposicao_id", sa.Integer(), nullable=False),
        sa.Column("resumo_leigo", sa.Text(), nullable=False),
        sa.Column("impacto_esperado", sa.Text(), nullable=False),
        sa.Column("areas_afetadas", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("argumentos_favor", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("argumentos_contra", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("provedor_llm", sa.String(50), nullable=False),
        sa.Column("modelo", sa.String(100), nullable=False),
        sa.Column("data_geracao", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("versao", sa.Integer(), server_default="1"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["proposicao_id"], ["proposicoes.id"]),
    )

    # eventos
    op.create_table(
        "eventos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("data_hora_inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data_hora_fim", sa.DateTime(timezone=True), nullable=True),
        sa.Column("situacao", sa.String(100), nullable=True),
        sa.Column("tipo", sa.String(100), nullable=True),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("pauta", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # assinaturas_rss
    op.create_table(
        "assinaturas_rss",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("email", sa.String(300), nullable=True),
        sa.Column("token", sa.String(64), nullable=False),
        sa.Column("filtro_temas", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("filtro_uf", sa.String(2), nullable=True),
        sa.Column("ativo", sa.Boolean(), server_default="true"),
        sa.Column("data_criacao", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("ultimo_acesso", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token", name="uq_assinatura_rss_token"),
    )

    # assinaturas_webhooks
    op.create_table(
        "assinaturas_webhooks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("secret", sa.String(128), nullable=False),
        sa.Column("eventos", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("filtro_temas", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("ativo", sa.Boolean(), server_default="true"),
        sa.Column("data_criacao", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("ultimo_dispatch", sa.DateTime(timezone=True), nullable=True),
        sa.Column("falhas_consecutivas", sa.Integer(), server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )

    # comparativos_votacao
    op.create_table(
        "comparativos_votacao",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("proposicao_id", sa.Integer(), nullable=False),
        sa.Column("votacao_camara_id", sa.Integer(), nullable=False),
        sa.Column("voto_popular_sim", sa.Integer(), server_default="0"),
        sa.Column("voto_popular_nao", sa.Integer(), server_default="0"),
        sa.Column("voto_popular_abstencao", sa.Integer(), server_default="0"),
        sa.Column("resultado_camara", sa.String(20), nullable=False),
        sa.Column("votos_camara_sim", sa.Integer(), server_default="0"),
        sa.Column("votos_camara_nao", sa.Integer(), server_default="0"),
        sa.Column("alinhamento", sa.Float(), server_default="0.5"),
        sa.Column("resumo_ia", sa.Text(), nullable=True),
        sa.Column("data_geracao", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["proposicao_id"], ["proposicoes.id"]),
        sa.ForeignKeyConstraint(["votacao_camara_id"], ["votacoes.id"]),
    )


def downgrade() -> None:
    """Drop all tables in reverse order."""
    op.drop_table("comparativos_votacao")
    op.drop_table("assinaturas_webhooks")
    op.drop_table("assinaturas_rss")
    op.drop_table("eventos")
    op.drop_table("analises_ia")
    op.drop_table("votos_populares")
    op.drop_table("eleitores")
    op.drop_table("partidos")
    op.drop_table("deputados")
    op.drop_table("votacoes")
    op.drop_table("proposicoes")
    sa.Enum("SIM", "NAO", "ABSTENCAO", name="votoenum").drop(op.get_bind())
