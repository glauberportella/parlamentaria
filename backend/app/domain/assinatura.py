"""Assinatura domain models — RSS and Webhook subscriptions."""

import uuid
from datetime import datetime

from sqlalchemy import String, Boolean, Integer, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AssinaturaRSS(Base):
    """RSS feed subscription for parliamentarians or organizations."""

    __tablename__ = "assinaturas_rss"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str | None] = mapped_column(String(300), nullable=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    filtro_temas: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    filtro_uf: Mapped[str | None] = mapped_column(String(2), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    data_criacao: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    ultimo_acesso: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<AssinaturaRSS {self.nome} ativo={self.ativo}>"


class AssinaturaWebhook(Base):
    """Outbound webhook subscription for external systems."""

    __tablename__ = "assinaturas_webhooks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    secret: Mapped[str] = mapped_column(String(128), nullable=False)
    eventos: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    filtro_temas: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    data_criacao: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    ultimo_dispatch: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    falhas_consecutivas: Mapped[int] = mapped_column(Integer, default=0)

    def __repr__(self) -> str:
        return f"<AssinaturaWebhook {self.nome} ativo={self.ativo}>"
