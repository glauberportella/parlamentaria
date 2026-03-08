"""Eleitor domain model — registered voter in the platform."""

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import String, Boolean, Date, DateTime, Enum, Integer, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class NivelVerificacao(str, enum.Enum):
    """Verification level of a registered voter.

    - NAO_VERIFICADO: Just created an account, minimal data.
    - AUTO_DECLARADO: Provided name, UF, CPF and birth date (self-declared).
    - VERIFICADO_TITULO: Also provided and validated a voter registration
      number (título de eleitor) — highest offline verification level.
    """

    NAO_VERIFICADO = "NAO_VERIFICADO"
    AUTO_DECLARADO = "AUTO_DECLARADO"
    VERIFICADO_TITULO = "VERIFICADO_TITULO"


class FrequenciaNotificacao(str, enum.Enum):
    """Notification frequency preference for periodic digests.

    - IMEDIATA: Receive alerts as soon as something relevant happens
      (existing behavior) PLUS daily digest.
    - DIARIA: Receive a daily digest at the preferred hour.
    - SEMANAL: Receive a weekly digest on Mondays (default for new users).
    - DESATIVADA: No periodic digests (still receives comparison results
      for propositions the user voted on).
    """

    IMEDIATA = "IMEDIATA"
    DIARIA = "DIARIA"
    SEMANAL = "SEMANAL"
    DESATIVADA = "DESATIVADA"


class Eleitor(Base):
    """A registered voter on the Parlamentaria platform.

    Voters can be either *eligible* (cidadão brasileiro, 16+ anos, verificado)
    or *non-eligible*.  Non-eligible users may still express opinions, but
    their votes are classified as ``OPINIAO`` and do not count in the
    official consolidated results sent to parliamentarians.

    Verification flows through progressive levels (NivelVerificacao):
    1. NAO_VERIFICADO — stub account from first interaction.
    2. AUTO_DECLARADO — provided name, UF, CPF, birth date, citizenship.
    3. VERIFICADO_TITULO — validated título de eleitor number.
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

    # --- Identity verification fields ---
    cpf_hash: Mapped[str | None] = mapped_column(
        String(64), unique=True, nullable=True,
        doc="SHA-256 hash of the CPF — ensures 1 person = 1 vote",
    )
    titulo_eleitor_hash: Mapped[str | None] = mapped_column(
        String(64), unique=True, nullable=True,
        doc="SHA-256 hash of the título de eleitor number",
    )
    nivel_verificacao: Mapped[NivelVerificacao] = mapped_column(
        Enum(NivelVerificacao),
        default=NivelVerificacao.NAO_VERIFICADO,
        server_default="NAO_VERIFICADO",
        doc="Progressive verification level",
    )

    # --- Notification preferences (engagement) ---
    frequencia_notificacao: Mapped[FrequenciaNotificacao] = mapped_column(
        Enum(FrequenciaNotificacao),
        default=FrequenciaNotificacao.SEMANAL,
        server_default="SEMANAL",
        doc="Preferred notification frequency: IMEDIATA, DIARIA, SEMANAL, DESATIVADA",
    )
    horario_preferido_notificacao: Mapped[int] = mapped_column(
        Integer,
        default=9,
        server_default="9",
        doc="Preferred hour (0-23) for receiving digest notifications",
    )
    ultimo_digest_enviado: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        doc="Timestamp of most recent digest sent to prevent duplicates",
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
        and account verified (at least AUTO_DECLARADO with CPF).
        """
        if not self.cidadao_brasileiro:
            return False
        if self.nivel_verificacao == NivelVerificacao.NAO_VERIFICADO:
            return False
        if self.cpf_hash is None:
            return False
        idade = self.idade
        if idade is None or idade < 16:
            return False
        return True

    def __repr__(self) -> str:
        return (
            f"<Eleitor {self.nome} ({self.uf}) "
            f"nivel={self.nivel_verificacao.value} elegivel={self.elegivel}>"
        )


from app.domain.voto_popular import VotoPopular  # noqa: E402, F401
