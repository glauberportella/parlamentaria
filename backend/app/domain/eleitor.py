"""Eleitor domain model — registered voter in the platform."""

import uuid
from datetime import date, datetime

from sqlalchemy import String, Boolean, Date, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Eleitor(Base):
    """A registered voter on the Parlamentaria platform.

    Voters can be either *eligible* (cidadão brasileiro, 16+ anos, verificado)
    or *non-eligible*.  Non-eligible users may still express opinions, but
    their votes are classified as ``OPINIAO`` and do not count in the
    official consolidated results sent to parliamentarians.
    """

    __tablename__ = "eleitores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(300), unique=True, nullable=False)
    uf: Mapped[str] = mapped_column(String(2), nullable=False, doc="Sigla do estado")
    chat_id: Mapped[str | None] = mapped_column(
        String(100), unique=True, nullable=True, doc="ID do chat no mensageiro"
    )
    channel: Mapped[str] = mapped_column(
        String(20), default="telegram", doc="Canal: telegram, whatsapp"
    )
    verificado: Mapped[bool] = mapped_column(Boolean, default=False)
    temas_interesse: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    # --- Eligibility fields (Fase limite-eleitor) ---
    data_nascimento: Mapped[date | None] = mapped_column(
        Date, nullable=True, doc="Data de nascimento para cálculo de idade (16+)"
    )
    cidadao_brasileiro: Mapped[bool] = mapped_column(
        Boolean, default=False, doc="Auto-declaração de cidadania brasileira"
    )

    data_cadastro: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    votos: Mapped[list["VotoPopular"]] = relationship(back_populates="eleitor", lazy="selectin")

    # --- Computed properties ---

    @property
    def idade(self) -> int | None:
        """Calculate age in years from data_nascimento."""
        if self.data_nascimento is None:
            return None
        today = date.today()
        born = self.data_nascimento
        return today.year - born.year - (
            (today.month, today.day) < (born.month, born.day)
        )

    @property
    def elegivel(self) -> bool:
        """Whether this voter is eligible for official popular votes.

        Criteria (CF/88 Art. 14): Brazilian citizen, 16+ years old,
        and account verified.
        """
        if not self.cidadao_brasileiro:
            return False
        if not self.verificado:
            return False
        idade = self.idade
        if idade is None or idade < 16:
            return False
        return True

    def __repr__(self) -> str:
        return f"<Eleitor {self.nome} ({self.uf}) elegivel={self.elegivel}>"


from app.domain.voto_popular import VotoPopular  # noqa: E402, F401
