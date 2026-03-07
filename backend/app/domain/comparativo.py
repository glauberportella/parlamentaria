"""ComparativoVotacao domain model — popular vs parliamentary vote comparison."""

import uuid
from datetime import datetime

from sqlalchemy import Integer, String, Text, Float, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ComparativoVotacao(Base):
    """Comparison between popular vote and actual parliamentary vote."""

    __tablename__ = "comparativos_votacao"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    proposicao_id: Mapped[int] = mapped_column(
        ForeignKey("proposicoes.id"), nullable=False
    )
    votacao_camara_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("votacoes.id"), nullable=False
    )
    voto_popular_sim: Mapped[int] = mapped_column(Integer, default=0)
    voto_popular_nao: Mapped[int] = mapped_column(Integer, default=0)
    voto_popular_abstencao: Mapped[int] = mapped_column(Integer, default=0)
    resultado_camara: Mapped[str] = mapped_column(
        String(20), nullable=False, doc="APROVADO ou REJEITADO"
    )
    votos_camara_sim: Mapped[int] = mapped_column(Integer, default=0)
    votos_camara_nao: Mapped[int] = mapped_column(Integer, default=0)
    alinhamento: Mapped[float] = mapped_column(
        Float, default=0.5, doc="0.0 (total divergência) a 1.0 (total alinhamento)"
    )
    resumo_ia: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_geracao: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<ComparativoVotacao prop={self.proposicao_id} alinhamento={self.alinhamento:.2f}>"
