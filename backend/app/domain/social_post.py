"""SocialPost domain model — social media post tracking."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RedeSocial(str, enum.Enum):
    """Supported social networks."""

    TWITTER = "twitter"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    DISCORD = "discord"
    REDDIT = "reddit"


class TipoPostSocial(str, enum.Enum):
    """Types of social media posts."""

    RESUMO_SEMANAL = "resumo_semanal"
    VOTACAO_RELEVANTE = "votacao_relevante"
    COMPARATIVO = "comparativo"
    DESTAQUE_PROPOSICAO = "destaque_proposicao"
    EXPLICATIVO_EDUCATIVO = "explicativo_educativo"


class StatusPost(str, enum.Enum):
    """Social post lifecycle status."""

    RASCUNHO = "rascunho"
    APROVADO = "aprovado"
    PUBLICADO = "publicado"
    FALHOU = "falhou"
    CANCELADO = "cancelado"


class SocialPost(Base):
    """Tracks social media posts generated and published by the system."""

    __tablename__ = "social_posts"
    __table_args__ = (
        UniqueConstraint(
            "tipo", "rede", "proposicao_id", "comparativo_id",
            name="uq_social_post_unique",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tipo: Mapped[TipoPostSocial] = mapped_column(
        Enum(TipoPostSocial), nullable=False
    )
    rede: Mapped[RedeSocial] = mapped_column(
        Enum(RedeSocial), nullable=False
    )
    proposicao_id: Mapped[int | None] = mapped_column(
        ForeignKey("proposicoes.id"), nullable=True
    )
    comparativo_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("comparativos_votacao.id"),
        nullable=True,
    )

    # Content
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    imagem_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    imagem_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Publication
    status: Mapped[StatusPost] = mapped_column(
        Enum(StatusPost), default=StatusPost.RASCUNHO, nullable=False
    )
    rede_post_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    publicado_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    erro: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metrics
    likes: Mapped[int] = mapped_column(Integer, default=0)
    shares: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    impressions: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<SocialPost {self.tipo.value}@{self.rede.value} status={self.status.value}>"
