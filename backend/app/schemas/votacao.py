"""Pydantic DTOs for Votação."""

from datetime import datetime

from pydantic import BaseModel, Field


class VotacaoBase(BaseModel):
    """Shared fields for vote session DTOs."""

    data: datetime
    descricao: str


class VotacaoCreate(VotacaoBase):
    """DTO for creating a vote session (from API sync)."""

    id: int = Field(..., description="ID from Câmara API")
    proposicao_id: int | None = None
    aprovacao: bool | None = None
    votos_sim: int = 0
    votos_nao: int = 0
    abstencoes: int = 0
    orientacoes: dict | None = None
    votos_parlamentares: dict | None = None


class VotacaoUpdate(BaseModel):
    """DTO for updating a vote session."""

    aprovacao: bool | None = None
    votos_sim: int | None = None
    votos_nao: int | None = None
    abstencoes: int | None = None
    orientacoes: dict | None = None
    votos_parlamentares: dict | None = None


class VotacaoResponse(VotacaoBase):
    """DTO for vote session response."""

    id: int
    proposicao_id: int | None = None
    aprovacao: bool | None = None
    votos_sim: int
    votos_nao: int
    abstencoes: int
    orientacoes: dict | None = None
    votos_parlamentares: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
