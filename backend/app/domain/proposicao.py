"""Proposição domain model."""

from datetime import date, datetime

from sqlalchemy import Integer, String, Text, Date, DateTime, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Proposicao(Base):
    """Legislative proposition from the Câmara dos Deputados."""

    __tablename__ = "proposicoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, doc="ID da API Câmara")
    tipo: Mapped[str] = mapped_column(String(20), nullable=False, doc="PL, PEC, MPV, PLP, etc.")
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    ano: Mapped[int] = mapped_column(Integer, nullable=False)
    ementa: Mapped[str] = mapped_column(Text, nullable=False)
    texto_completo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    data_apresentacao: Mapped[date] = mapped_column(Date, nullable=False)
    situacao: Mapped[str] = mapped_column(String(200), nullable=False, default="Em tramitação")
    temas: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    autores: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    resumo_ia: Mapped[str | None] = mapped_column(Text, nullable=True)
    ultima_sincronizacao: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    analises: Mapped[list["AnaliseIA"]] = relationship(back_populates="proposicao", lazy="selectin")
    votos_populares: Mapped[list["VotoPopular"]] = relationship(
        back_populates="proposicao", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Proposicao {self.tipo} {self.numero}/{self.ano}>"


# Avoid circular imports — these are resolved at runtime by SQLAlchemy
from app.domain.analise_ia import AnaliseIA  # noqa: E402, F401
from app.domain.voto_popular import VotoPopular  # noqa: E402, F401
