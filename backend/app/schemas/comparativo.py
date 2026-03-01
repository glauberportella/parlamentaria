"""Pydantic DTOs for ComparativoVotacao."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ComparativoCreate(BaseModel):
    """DTO for creating a comparative analysis."""

    proposicao_id: int
    votacao_camara_id: int
    voto_popular_sim: int = 0
    voto_popular_nao: int = 0
    voto_popular_abstencao: int = 0
    resultado_camara: str = Field(..., description="APROVADO ou REJEITADO")
    votos_camara_sim: int = 0
    votos_camara_nao: int = 0
    alinhamento: float = Field(0.5, ge=0.0, le=1.0)
    resumo_ia: str | None = None


class ComparativoResponse(BaseModel):
    """DTO for comparative analysis response."""

    id: uuid.UUID
    proposicao_id: int
    votacao_camara_id: int
    voto_popular_sim: int
    voto_popular_nao: int
    voto_popular_abstencao: int
    resultado_camara: str
    votos_camara_sim: int
    votos_camara_nao: int
    alinhamento: float
    resumo_ia: str | None = None
    data_geracao: datetime

    model_config = {"from_attributes": True}
