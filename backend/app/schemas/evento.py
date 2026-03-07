"""Pydantic DTOs for Evento."""

from datetime import datetime

from pydantic import BaseModel, Field


class EventoBase(BaseModel):
    """Shared fields for event DTOs."""

    descricao: str
    tipo_evento: str | None = None


class EventoResponse(EventoBase):
    """DTO for event response."""

    id: int
    data_inicio: datetime
    data_fim: datetime | None = None
    local: str | None = None
    situacao: str | None = None
    pauta: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
