"""ExportJob domain model — async export processing via Celery."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ExportJobStatus(str, enum.Enum):
    """Status of an export job."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


class ExportJobType(str, enum.Enum):
    """Type of export data."""

    VOTOS = "VOTOS"
    COMPARATIVOS = "COMPARATIVOS"


class ExportJob(Base):
    """Async export job — processed by Celery, downloadable when complete."""

    __tablename__ = "export_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    parlamentar_user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), nullable=False, index=True,
        doc="ID do ParlamentarUser que solicitou a exportação",
    )
    tipo: Mapped[ExportJobType] = mapped_column(
        Enum(ExportJobType, name="export_job_type"), nullable=False,
    )
    status: Mapped[ExportJobStatus] = mapped_column(
        Enum(ExportJobStatus, name="export_job_status"),
        nullable=False,
        default=ExportJobStatus.PENDING,
        server_default="PENDING",
    )
    filtros: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        doc="Filtros aplicados na exportação (proposicao_id, resultado, tipo_voto, etc.)",
    )
    total_rows: Mapped[int | None] = mapped_column(
        Integer, nullable=True, doc="Total de linhas exportadas",
    )
    file_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True, doc="Nome do arquivo gerado",
    )
    file_size_bytes: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, doc="Mensagem de erro (se status = FAILED)",
    )
    notificado_email: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false",
        doc="Se o usuário já foi notificado por email",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        doc="Quando o arquivo expira e será removido pelo cleanup",
    )

    def __repr__(self) -> str:
        return f"<ExportJob {self.id} tipo={self.tipo.value} status={self.status.value}>"
