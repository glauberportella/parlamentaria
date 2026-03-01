"""Pydantic DTOs for Assinatura (RSS and Webhook)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


# --- RSS ---


class AssinaturaRSSCreate(BaseModel):
    """DTO for creating an RSS subscription."""

    nome: str = Field(..., max_length=200)
    email: str | None = Field(None, max_length=300)
    filtro_temas: list[str] | None = None
    filtro_uf: str | None = Field(None, min_length=2, max_length=2)


class AssinaturaRSSResponse(BaseModel):
    """DTO for RSS subscription response."""

    id: uuid.UUID
    nome: str
    email: str | None = None
    token: str
    filtro_temas: list[str] | None = None
    filtro_uf: str | None = None
    ativo: bool
    data_criacao: datetime
    ultimo_acesso: datetime | None = None

    model_config = {"from_attributes": True}


# --- Webhook ---


class AssinaturaWebhookCreate(BaseModel):
    """DTO for creating a webhook subscription."""

    nome: str = Field(..., max_length=200)
    url: str = Field(..., max_length=500)
    eventos: list[str] = Field(..., min_length=1)
    filtro_temas: list[str] | None = None


class AssinaturaWebhookResponse(BaseModel):
    """DTO for webhook subscription response."""

    id: uuid.UUID
    nome: str
    url: str
    eventos: list[str]
    filtro_temas: list[str] | None = None
    ativo: bool
    data_criacao: datetime
    ultimo_dispatch: datetime | None = None
    falhas_consecutivas: int

    model_config = {"from_attributes": True}
