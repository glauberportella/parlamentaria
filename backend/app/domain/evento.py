"""Evento domain model — plenary events from the Câmara."""

from datetime import datetime

from sqlalchemy import Integer, String, Text, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Evento(Base):
    """A plenary event at the Câmara dos Deputados."""

    __tablename__ = "eventos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, doc="ID da API Câmara")
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    tipo_evento: Mapped[str | None] = mapped_column(String(100), nullable=True)
    data_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    data_fim: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    local: Mapped[str | None] = mapped_column(String(200), nullable=True)
    situacao: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pauta: Mapped[dict | None] = mapped_column(JSONB, nullable=True, doc="Items em pauta")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Evento {self.id} - {self.descricao[:50]}>"
