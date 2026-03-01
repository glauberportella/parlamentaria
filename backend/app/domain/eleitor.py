"""Eleitor domain model — registered voter in the platform."""

import uuid
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Eleitor(Base):
    """A registered voter on the Parlamentaria platform."""

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
    data_cadastro: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    votos: Mapped[list["VotoPopular"]] = relationship(back_populates="eleitor", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Eleitor {self.nome} ({self.uf})>"


from app.domain.voto_popular import VotoPopular  # noqa: E402, F401
