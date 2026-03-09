"""ParlamentarUser domain model — Dashboard authentication."""

import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TipoParlamentarUser(str, enum.Enum):
    """Type of user accessing the parliamentarian dashboard."""

    DEPUTADO = "DEPUTADO"
    ASSESSOR = "ASSESSOR"
    LIDERANCA = "LIDERANCA"


class ParlamentarUser(Base):
    """A user of the parliamentarian dashboard (deputado, assessor or liderança)."""

    __tablename__ = "parlamentar_users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
        doc="UUID do usuário parlamentar",
    )
    deputado_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("deputados.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="FK para deputado vinculado (pode ser nulo para lideranças de partido)",
    )
    email: Mapped[str] = mapped_column(
        String(200), nullable=False, unique=True, index=True
    )
    nome: Mapped[str] = mapped_column(String(300), nullable=False)
    cargo: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        doc="Cargo descritivo (ex: Deputado Federal, Assessor Parlamentar)",
    )
    tipo: Mapped[TipoParlamentarUser] = mapped_column(
        Enum(TipoParlamentarUser, name="tipo_parlamentar_user"),
        nullable=False,
        default=TipoParlamentarUser.ASSESSOR,
    )
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    codigo_convite: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        unique=True,
        doc="Código de convite para primeiro acesso (uso único)",
    )
    convite_usado: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    ultimo_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    temas_acompanhados: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True, doc="Temas legislativos que o usuário acompanha"
    )
    notificacoes_email: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    refresh_token_hash: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        doc="Hash do refresh token ativo (para revogação)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    deputado = relationship("Deputado", lazy="selectin")

    def __repr__(self) -> str:
        return f"<ParlamentarUser {self.nome} ({self.tipo.value})>"
