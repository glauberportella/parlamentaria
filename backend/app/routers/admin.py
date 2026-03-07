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
from app.schemas.deputado import DeputadoResponse
from app.schemas.partido import PartidoResponse
from app.schemas.evento import EventoResponse
from app.services.proposicao_service import ProposicaoService
from app.services.analise_service import AnaliseIAService
from app.services.eleitor_service import EleitorService
from app.services.deputado_service import DeputadoService
from app.services.partido_service import PartidoService
from app.services.evento_service import EventoService
from app.services.voto_popular_service import VotoPopularService
from app.services.comparativo_service import ComparativoService
from app.schemas.analise_ia import AnaliseIAResponse

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
    """Get consolidated popular vote result for a proposition.

    Returns both the official result (eligible voters only) and
    the consultive result (all votes including opinions).
    """
    service = VotoPopularService(db)
    return await service.obter_resultado_completo(proposicao_id)


@router.post("/proposicoes/{proposicao_id}/analisar", dependencies=[Depends(verify_api_key)])
@limiter.limit("10/minute")
async def trigger_analise(
    request: Request,
    proposicao_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Trigger IA analysis for a proposition.

    Validates that the proposition exists and enqueues a Celery task
    to call the LLM and generate a structured analysis.
    """
    # Validate proposition exists
    service = ProposicaoService(db)
    await service.get_by_id(proposicao_id)  # raises NotFoundException

    from app.tasks.generate_analysis import generate_analysis_task
    generate_analysis_task.delay(proposicao_id=proposicao_id)
    return {"status": "queued", "proposicao_id": proposicao_id}


@router.get("/proposicoes/{proposicao_id}/analise", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
async def get_analise(
    request: Request,
    proposicao_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the latest AI analysis for a proposition."""
    service = AnaliseIAService(db)
    analise = await service.get_latest_or_raise(proposicao_id)
    return {
        "status": "success",
        "analise": AnaliseIAResponse.model_validate(analise),
    }


@router.get("/proposicoes/{proposicao_id}/analise/versoes", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
async def list_analise_versions(
    request: Request,
    proposicao_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all AI analysis versions for a proposition."""
    service = AnaliseIAService(db)
    versions = await service.list_versions(proposicao_id)
    return {
        "total": len(versions),
        "items": [AnaliseIAResponse.model_validate(v) for v in versions],
    }


@router.post("/analises/reanalyze", dependencies=[Depends(verify_api_key)])
@limiter.limit("2/minute")
async def trigger_reanalyze_all(request: Request) -> dict:
    """Re-analyze all propositions (creates new version for each).

    Useful when the model or prompt has been updated.
    """
    from app.tasks.generate_analysis import reanalyze_all_task
    reanalyze_all_task.delay()
    return {"status": "queued", "message": "Re-analysis of all propositions triggered."}


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


# ------------------------------------------------------------------
# Deputados
# ------------------------------------------------------------------


@router.get("/deputados", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
async def list_deputados(
    request: Request,
    sigla_partido: str | None = Query(None),
    sigla_uf: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List synced deputies (admin only)."""
    service = DeputadoService(db)
    deputados = await service.list_deputados(sigla_partido=sigla_partido, sigla_uf=sigla_uf)
    return {
        "total": len(deputados),
        "items": [DeputadoResponse.model_validate(d) for d in deputados],
    }


@router.post("/sync/deputados", dependencies=[Depends(verify_api_key)])
@limiter.limit("5/minute")
async def sync_deputados(
    request: Request,
    sigla_uf: str | None = Query(None, description="Filtrar por UF"),
    sigla_partido: str | None = Query(None, description="Filtrar por partido"),
) -> dict:
    """Trigger deputy sync from the Câmara API via Celery task."""
    from app.tasks.sync_deputados import sync_deputados_task

    sync_deputados_task.delay(sigla_uf=sigla_uf, sigla_partido=sigla_partido)
    return {
        "status": "queued",
        "message": "Sincronização de deputados enfileirada.",
        "filters": {"sigla_uf": sigla_uf, "sigla_partido": sigla_partido},
    }


# ------------------------------------------------------------------
# Partidos
# ------------------------------------------------------------------


@router.get("/partidos", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
async def list_partidos(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List synced political parties (admin only)."""
    service = PartidoService(db)
    partidos = await service.list_partidos()
    return {
        "total": len(partidos),
        "items": [PartidoResponse.model_validate(p) for p in partidos],
    }


@router.post("/sync/partidos", dependencies=[Depends(verify_api_key)])
@limiter.limit("5/minute")
async def sync_partidos(request: Request) -> dict:
    """Trigger political party sync from the Câmara API via Celery task."""
    from app.tasks.sync_partidos import sync_partidos_task

    sync_partidos_task.delay()
    return {
        "status": "queued",
        "message": "Sincronização de partidos enfileirada.",
    }


# ------------------------------------------------------------------
# Eventos
# ------------------------------------------------------------------


@router.get("/eventos", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
async def list_eventos(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List recent plenary events (admin only)."""
    service = EventoService(db)
    eventos = await service.list_recent(limit=limit)
    return {
        "total": len(eventos),
        "items": [EventoResponse.model_validate(e) for e in eventos],
    }


@router.post("/sync/eventos", dependencies=[Depends(verify_api_key)])
@limiter.limit("5/minute")
async def sync_eventos(
    request: Request,
    dias_atras: int = Query(7, ge=1, le=90, description="Dias retroativos para sincronizar"),
) -> dict:
    """Trigger plenary event sync from the Câmara API via Celery task."""
    from app.tasks.sync_eventos import sync_eventos_task

    sync_eventos_task.delay(dias_atras=dias_atras)
    return {
        "status": "queued",
        "message": f"Sincronização de eventos ({dias_atras} dias) enfileirada.",
        "filters": {"dias_atras": dias_atras},
    }


# ------------------------------------------------------------------
# Sync Geral (proposições + votações)
# ------------------------------------------------------------------


@router.post("/sync/proposicoes", dependencies=[Depends(verify_api_key)])
@limiter.limit("5/minute")
async def sync_proposicoes(
    request: Request,
    ano: int | None = Query(None, description="Ano das proposições"),
    sigla_tipo: str | None = Query(None, description="Tipo (PL, PEC, MPV, etc.)"),
) -> dict:
    """Trigger proposição sync from the Câmara API via Celery task."""
    from app.tasks.sync_proposicoes import sync_proposicoes_task

    sync_proposicoes_task.delay(ano=ano, sigla_tipo=sigla_tipo)
    return {
        "status": "queued",
        "message": "Sincronização de proposições enfileirada.",
        "filters": {"ano": ano, "sigla_tipo": sigla_tipo},
    }


@router.post("/sync/votacoes", dependencies=[Depends(verify_api_key)])
@limiter.limit("5/minute")
async def sync_votacoes(request: Request) -> dict:
    """Trigger votação sync from the Câmara API via Celery task."""
    from app.tasks.sync_votacoes import sync_votacoes_task

    sync_votacoes_task.delay()
    return {
        "status": "queued",
        "message": "Sincronização de votações enfileirada.",
    }


@router.post("/sync/all", dependencies=[Depends(verify_api_key)])
@limiter.limit("2/minute")
async def sync_all(request: Request) -> dict:
    """Trigger full sync of all entities from the Câmara API.

    Enqueues separate Celery tasks for: proposições, votações,
    deputados, partidos and eventos.
    """
    from app.tasks.sync_proposicoes import sync_proposicoes_task
    from app.tasks.sync_votacoes import sync_votacoes_task
    from app.tasks.sync_deputados import sync_deputados_task
    from app.tasks.sync_partidos import sync_partidos_task
    from app.tasks.sync_eventos import sync_eventos_task

    sync_proposicoes_task.delay()
    sync_votacoes_task.delay()
    sync_deputados_task.delay()
    sync_partidos_task.delay()
    sync_eventos_task.delay()

    return {
        "status": "queued",
        "message": "Sincronização completa enfileirada (proposições, votações, deputados, partidos, eventos).",
    }


# ------------------------------------------------------------------
# RAG / Embeddings Admin
# ------------------------------------------------------------------


@router.get("/rag/stats", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
async def rag_stats(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get RAG index statistics."""
    from app.services.rag_service import RAGService

    service = RAGService(db)
    return await service.get_index_stats()


@router.post("/rag/reindex", dependencies=[Depends(verify_api_key)])
@limiter.limit("5/minute")
async def rag_reindex(
    request: Request,
    proposicao_id: int | None = Query(None, description="Index single proposição, or all if omitted"),
) -> dict:
    """Trigger RAG re-indexing via Celery task."""
    from app.tasks.generate_embeddings import generate_embeddings_task, reindex_all_embeddings_task

    if proposicao_id is not None:
        generate_embeddings_task.delay(proposicao_id=proposicao_id)
        return {"status": "queued", "proposicao_id": proposicao_id}
    else:
        reindex_all_embeddings_task.delay()
        return {"status": "queued", "message": "Full re-index triggered."}


@router.post("/rag/search", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
async def rag_search(
    request: Request,
    query: str = Query(..., min_length=3, description="Natural language search query"),
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Test semantic search (admin debugging tool)."""
    from app.services.rag_service import RAGService

    service = RAGService(db)
    results = await service.search_proposicoes(query=query, limit=limit)
    return {"query": query, "total": len(results), "results": results}
