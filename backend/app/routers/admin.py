"""Admin endpoints — protected by API key."""

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_db
from app.exceptions import UnauthorizedException
from app.schemas.proposicao import ProposicaoResponse
from app.schemas.eleitor import EleitorResponse
from app.schemas.comparativo import ComparativoResponse
from app.services.proposicao_service import ProposicaoService
from app.services.eleitor_service import EleitorService
from app.services.voto_popular_service import VotoPopularService
from app.services.comparativo_service import ComparativoService

router = APIRouter(prefix="/admin", tags=["admin"])


async def verify_api_key(x_api_key: str = Header(...)) -> str:
    """Validate the admin API key from the request header."""
    if x_api_key != settings.admin_api_key:
        raise UnauthorizedException("API key inválida")
    return x_api_key


@router.get("/proposicoes", dependencies=[Depends(verify_api_key)])
async def list_proposicoes(
    tipo: str | None = Query(None),
    ano: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List synced proposições (admin only)."""
    service = ProposicaoService(db)
    proposicoes = await service.list_proposicoes(tipo=tipo, ano=ano)
    return {
        "total": len(proposicoes),
        "items": [ProposicaoResponse.model_validate(p) for p in proposicoes],
    }


@router.get("/eleitores", dependencies=[Depends(verify_api_key)])
async def list_eleitores(
    uf: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List registered eleitores (admin only)."""
    service = EleitorService(db)
    eleitores = await service.list_eleitores(uf=uf)
    return {
        "total": len(eleitores),
        "items": [EleitorResponse.model_validate(e) for e in eleitores],
    }


@router.get("/votacoes/resultado/{proposicao_id}", dependencies=[Depends(verify_api_key)])
async def get_resultado_votacao(
    proposicao_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get consolidated popular vote result for a proposition."""
    service = VotoPopularService(db)
    return await service.obter_resultado(proposicao_id)


@router.post("/proposicoes/{proposicao_id}/analisar", dependencies=[Depends(verify_api_key)])
async def trigger_analise(
    proposicao_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Trigger IA analysis for a proposition (placeholder)."""
    # TODO: Integrate with AnaliseIAService + LLM in Fase 3
    return {"status": "queued", "proposicao_id": proposicao_id}


@router.get("/comparativos", dependencies=[Depends(verify_api_key)])
async def list_comparativos(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List pop vs real vote comparatives."""
    from sqlalchemy import select
    from app.domain.comparativo import ComparativoVotacao

    stmt = select(ComparativoVotacao).order_by(ComparativoVotacao.data_geracao.desc()).limit(100)
    result = await db.execute(stmt)
    comparativos = result.scalars().all()
    return {
        "total": len(comparativos),
        "items": [ComparativoResponse.model_validate(c) for c in comparativos],
    }
