"""Pydantic DTOs for Deputado."""

from datetime import datetime

from pydantic import BaseModel, Field


class DeputadoBase(BaseModel):
    """Shared fields for deputy DTOs."""

    nome: str = Field(..., max_length=200)


class DeputadoCreate(DeputadoBase):
    """DTO for creating a deputy (from API sync)."""

    id: int = Field(..., description="ID from Câmara API")
    nome_civil: str | None = None
    sigla_partido: str | None = None
    sigla_uf: str | None = None
    foto_url: str | None = None
    email: str | None = None
    situacao: str | None = None
    dados_extras: dict | None = None


class DeputadoUpdate(BaseModel):
    """DTO for updating a deputy."""

    nome: str | None = None
    sigla_partido: str | None = None
    sigla_uf: str | None = None
    foto_url: str | None = None
    email: str | None = None
    situacao: str | None = None
    dados_extras: dict | None = None


class DeputadoResponse(DeputadoBase):
    """DTO for deputy response."""

    id: int
    nome_civil: str | None = None
    sigla_partido: str | None = None
    sigla_uf: str | None = None
    foto_url: str | None = None
    email: str | None = None
    situacao: str | None = None
    dados_extras: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
