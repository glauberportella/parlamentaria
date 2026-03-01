"""Partido domain model."""

from datetime import datetime

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Partido(Base):
    """A political party."""

    __tablename__ = "partidos"

    id: Mapped[int] = mapped_column(primary_key=True, doc="ID da API Câmara")
    sigla: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Partido {self.sigla}>"
