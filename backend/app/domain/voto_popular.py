"""VotoPopular domain model — citizen vote on a proposition."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, Enum, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class VotoEnum(str, enum.Enum):
    """Possible values for a popular vote."""

    SIM = "SIM"
    NAO = "NAO"
    ABSTENCAO = "ABSTENCAO"


class VotoPopular(Base):
    """A citizen's vote on a legislative proposition."""

    __tablename__ = "votos_populares"
    __table_args__ = (
        UniqueConstraint("eleitor_id", "proposicao_id", name="uq_eleitor_proposicao"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    eleitor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("eleitores.id"), nullable=False
    )
    proposicao_id: Mapped[int] = mapped_column(
        ForeignKey("proposicoes.id"), nullable=False
    )
    voto: Mapped[VotoEnum] = mapped_column(Enum(VotoEnum), nullable=False)
    justificativa: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_voto: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    eleitor: Mapped["Eleitor"] = relationship(back_populates="votos")
    proposicao: Mapped["Proposicao"] = relationship(back_populates="votos_populares")

    def __repr__(self) -> str:
        return f"<VotoPopular {self.voto.value} eleitor={self.eleitor_id}>"


from app.domain.eleitor import Eleitor  # noqa: E402, F401
from app.domain.proposicao import Proposicao  # noqa: E402, F401
