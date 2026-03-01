"""Pydantic DTOs for AnaliseIA."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AnaliseIACreate(BaseModel):
    """DTO for creating an AI analysis."""

    proposicao_id: int
    resumo_leigo: str
    impacto_esperado: str
    areas_afetadas: list[str]
    argumentos_favor: list[str]
    argumentos_contra: list[str]
    provedor_llm: str
    modelo: str


class AnaliseIAResponse(BaseModel):
    """DTO for AI analysis response."""

    id: uuid.UUID
    proposicao_id: int
    resumo_leigo: str
    impacto_esperado: str
    areas_afetadas: list[str]
    argumentos_favor: list[str]
    argumentos_contra: list[str]
    provedor_llm: str
    modelo: str
    data_geracao: datetime
    versao: int

    model_config = {"from_attributes": True}
