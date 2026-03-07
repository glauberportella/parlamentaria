"""Pydantic DTOs for Partido."""

from datetime import datetime

from pydantic import BaseModel, Field


class PartidoBase(BaseModel):
    """Shared fields for party DTOs."""

    sigla: str = Field(..., max_length=20)
    nome: str = Field(..., max_length=200)


class PartidoResponse(PartidoBase):
    """DTO for party response."""

    id: int
    created_at: datetime

    model_config = {"from_attributes": True}
