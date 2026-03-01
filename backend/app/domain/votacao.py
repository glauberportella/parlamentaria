"""Votação domain model — parliamentary votes from the Câmara."""

from datetime import datetime

from sqlalchemy import Integer, String, Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Votacao(Base):
    """A parliamentary vote session from the Câmara dos Deputados."""

    __tablename__ = "votacoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, doc="ID da API Câmara")
    proposicao_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("proposicoes.id"), nullable=True
    )
    data: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    aprovacao: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    votos_sim: Mapped[int] = mapped_column(Integer, default=0)
    votos_nao: Mapped[int] = mapped_column(Integer, default=0)
    abstencoes: Mapped[int] = mapped_column(Integer, default=0)
    orientacoes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    votos_parlamentares: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Votacao {self.id} - {self.descricao[:50]}>"
