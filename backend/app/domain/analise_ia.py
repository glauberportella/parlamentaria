"""AnaliseIA domain model — AI-generated analysis of a proposition."""

import uuid
from datetime import datetime

from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AnaliseIA(Base):
    """AI-generated analysis of a legislative proposition."""

    __tablename__ = "analises_ia"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    proposicao_id: Mapped[int] = mapped_column(
        ForeignKey("proposicoes.id"), nullable=False
    )
    resumo_leigo: Mapped[str] = mapped_column(Text, nullable=False)
    impacto_esperado: Mapped[str] = mapped_column(Text, nullable=False)
    areas_afetadas: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    argumentos_favor: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    argumentos_contra: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    provedor_llm: Mapped[str] = mapped_column(String(50), nullable=False)
    modelo: Mapped[str] = mapped_column(String(100), nullable=False)
    data_geracao: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    versao: Mapped[int] = mapped_column(Integer, default=1)

    # Relationships
    proposicao: Mapped["Proposicao"] = relationship(back_populates="analises")

    def __repr__(self) -> str:
        return f"<AnaliseIA prop={self.proposicao_id} v{self.versao}>"


from app.domain.proposicao import Proposicao  # noqa: E402, F401
