"""Admin endpoints — protected by API key."""

from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_db
from app.exceptions import UnauthorizedException
from app.middleware import limiter
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
@limiter.limit("30/minute")
async def list_proposicoes(
    request: Request,
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
@limiter.limit("30/minute")
async def list_eleitores(
    request: Request,
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
@limiter.limit("30/minute")
async def get_resultado_votacao(
    request: Request,
    proposicao_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get consolidated popular vote result for a proposition."""
    service = VotoPopularService(db)
    return await service.obter_resultado(proposicao_id)


@router.post("/proposicoes/{proposicao_id}/analisar", dependencies=[Depends(verify_api_key)])
@limiter.limit("10/minute")
async def trigger_analise(
    request: Request,
    proposicao_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Trigger IA analysis for a proposition (placeholder)."""
    # TODO: Integrate with AnaliseIAService + LLM in Fase 3
    return {"status": "queued", "proposicao_id": proposicao_id}


@router.get("/comparativos", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
async def list_comparativos(
    request: Request,
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List pop vs real vote comparatives."""
    service = ComparativoService(db)
    comparativos = await service.list_recent(limit=limit)
    return {
        "total": len(comparativos),
        "items": [ComparativoResponse.model_validate(c) for c in comparativos],
    }
