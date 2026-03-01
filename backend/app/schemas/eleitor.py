"""Pydantic DTOs for Eleitor."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class EleitorBase(BaseModel):
    """Shared fields for voter DTOs."""

    nome: str = Field(..., max_length=200)
    email: str = Field(..., max_length=300)
    uf: str = Field(..., min_length=2, max_length=2)


class EleitorCreate(EleitorBase):
    """DTO for creating a voter."""

    chat_id: str | None = None
    channel: str = "telegram"
    temas_interesse: list[str] | None = None


class EleitorUpdate(BaseModel):
    """DTO for updating a voter."""

    nome: str | None = None
    uf: str | None = Field(None, min_length=2, max_length=2)
    chat_id: str | None = None
    channel: str | None = None
    verificado: bool | None = None
    temas_interesse: list[str] | None = None


class EleitorResponse(EleitorBase):
    """DTO for voter response."""

    id: uuid.UUID
    chat_id: str | None = None
    channel: str
    verificado: bool
    temas_interesse: list[str] | None = None
    data_cadastro: datetime

    model_config = {"from_attributes": True}
