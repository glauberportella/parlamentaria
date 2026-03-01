"""Deputado domain model."""

from datetime import datetime

from sqlalchemy import Integer, String, Text, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Deputado(Base):
    """A federal deputy from the Câmara dos Deputados."""

    __tablename__ = "deputados"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, doc="ID da API Câmara")
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    nome_civil: Mapped[str | None] = mapped_column(String(300), nullable=True)
    sigla_partido: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sigla_uf: Mapped[str | None] = mapped_column(String(2), nullable=True)
    foto_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    situacao: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dados_extras: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Deputado {self.nome} ({self.sigla_partido}-{self.sigla_uf})>"
