"""Pydantic DTOs for VotoPopular."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.voto_popular import VotoEnum, TipoVoto


class VotoPopularCreate(BaseModel):
    """DTO for casting a popular vote."""

    eleitor_id: uuid.UUID
    proposicao_id: int
    voto: VotoEnum
    justificativa: str | None = None


class VotoPopularResponse(BaseModel):
    """DTO for popular vote response."""

    id: uuid.UUID
    eleitor_id: uuid.UUID
    proposicao_id: int
    voto: VotoEnum
    tipo_voto: TipoVoto = TipoVoto.OPINIAO
    justificativa: str | None = None
    data_voto: datetime

    model_config = {"from_attributes": True}


class ResultadoVotacaoPopular(BaseModel):
    """Aggregated result of popular votes on a proposition."""

    proposicao_id: int
    total_sim: int
    total_nao: int
    total_abstencao: int
    total_votos: int
    percentual_sim: float
    percentual_nao: float
    percentual_abstencao: float


class ResultadoVotacaoOficial(BaseModel):
    """Aggregated result of OFICIAL (eligible) votes only.

    This is the result published to parliamentarians via RSS/Webhooks.
    """

    proposicao_id: int
    total_sim: int
    total_nao: int
    total_abstencao: int
    total_votos: int
    percentual_sim: float
    percentual_nao: float
    percentual_abstencao: float


class ResultadoVotacaoCompleto(BaseModel):
    """Full voting result with official + consultive breakdown."""

    proposicao_id: int
    oficial: ResultadoVotacaoOficial
    consultivo: ResultadoVotacaoPopular

