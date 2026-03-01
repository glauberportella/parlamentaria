"""Pydantic DTOs for Proposição."""

from datetime import date, datetime

from pydantic import BaseModel, Field


class ProposicaoBase(BaseModel):
    """Shared fields for proposition DTOs."""

    tipo: str = Field(..., max_length=20, description="PL, PEC, MPV, PLP, etc.")
    numero: int
    ano: int
    ementa: str


class ProposicaoCreate(ProposicaoBase):
    """DTO for creating a proposition (from API sync)."""

    id: int = Field(..., description="ID from Câmara API")
    texto_completo_url: str | None = None
    data_apresentacao: date
    situacao: str = "Em tramitação"
    temas: list[str] | None = None
    autores: dict | None = None


class ProposicaoUpdate(BaseModel):
    """DTO for updating a proposition."""

    ementa: str | None = None
    situacao: str | None = None
    temas: list[str] | None = None
    autores: dict | None = None
    resumo_ia: str | None = None
    texto_completo_url: str | None = None


class ProposicaoResponse(ProposicaoBase):
    """DTO for proposition response."""

    id: int
    texto_completo_url: str | None = None
    data_apresentacao: date
    situacao: str
    temas: list[str] | None = None
    autores: dict | None = None
    resumo_ia: str | None = None
    ultima_sincronizacao: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class ProposicaoListResponse(BaseModel):
    """Paginated list of propositions."""

    items: list[ProposicaoResponse]
    total: int
