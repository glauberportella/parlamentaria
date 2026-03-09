"""Export endpoints for the parlamentar dashboard.

Provides CSV export for votos and comparativos data.
"""

import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.domain.comparativo import ComparativoVotacao
from app.domain.proposicao import Proposicao
from app.domain.voto_popular import VotoPopular
from app.domain.eleitor import Eleitor
from app.logging import get_logger
from app.routers.parlamentar.auth import get_current_parlamentar_user
from app.schemas.parlamentar import ParlamentarUserResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/exportar", tags=["parlamentar-export"])


def _csv_response(buffer: io.StringIO, filename: str) -> StreamingResponse:
    """Build a StreamingResponse for CSV download."""
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _parse_temas(temas_raw) -> list[str]:
    """Parse temas that may be list or JSON string (cross-DB)."""
    if temas_raw is None:
        return []
    if isinstance(temas_raw, list):
        return temas_raw
    if isinstance(temas_raw, str):
        import json

        try:
            parsed = json.loads(temas_raw)
            return parsed if isinstance(parsed, list) else []
        except (json.JSONDecodeError, TypeError):
            return []
    return []


@router.get("/votos")
async def exportar_votos(
    proposicao_id: int | None = Query(None, description="Filtrar por proposição"),
    db: AsyncSession = Depends(get_db),
    _current_user: ParlamentarUserResponse = Depends(get_current_parlamentar_user),
) -> StreamingResponse:
    """Export votos populares as CSV.

    Columns: proposicao_tipo, proposicao_numero, proposicao_ano, ementa, voto,
    tipo_voto, uf_eleitor, data_voto.
    Electors are anonymised (only UF is exported).
    """
    stmt = (
        select(
            Proposicao.tipo,
            Proposicao.numero,
            Proposicao.ano,
            Proposicao.ementa,
            VotoPopular.voto,
            VotoPopular.tipo_voto,
            Eleitor.uf,
            VotoPopular.data_voto,
        )
        .join(Proposicao, VotoPopular.proposicao_id == Proposicao.id)
        .join(Eleitor, VotoPopular.eleitor_id == Eleitor.id)
    )

    if proposicao_id:
        stmt = stmt.where(VotoPopular.proposicao_id == proposicao_id)

    stmt = stmt.order_by(VotoPopular.data_voto.desc()).limit(50_000)

    result = await db.execute(stmt)
    rows = result.all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "tipo",
        "numero",
        "ano",
        "ementa",
        "voto",
        "tipo_voto",
        "uf_eleitor",
        "data_voto",
    ])
    for row in rows:
        data_str = row.data_voto.isoformat() if row.data_voto else ""
        writer.writerow([
            row.tipo or "",
            row.numero or "",
            row.ano or "",
            (row.ementa or "")[:200],
            row.voto or "",
            row.tipo_voto or "",
            row.uf or "",
            data_str,
        ])

    ts = datetime.now(timezone.utc).strftime("%Y%m%d")
    suffix = f"_prop{proposicao_id}" if proposicao_id else ""
    return _csv_response(buf, f"votos_populares{suffix}_{ts}.csv")


@router.get("/comparativos")
async def exportar_comparativos(
    resultado: str | None = Query(None, description="APROVADO ou REJEITADO"),
    db: AsyncSession = Depends(get_db),
    _current_user: ParlamentarUserResponse = Depends(get_current_parlamentar_user),
) -> StreamingResponse:
    """Export comparativos as CSV.

    Columns: proposicao, ementa, temas, resultado_camara,
    voto_pop_sim, voto_pop_nao, voto_pop_abstencao,
    votos_camara_sim, votos_camara_nao, alinhamento, data.
    """
    stmt = (
        select(
            ComparativoVotacao,
            Proposicao.tipo,
            Proposicao.numero,
            Proposicao.ano,
            Proposicao.ementa,
            Proposicao.temas,
        )
        .join(Proposicao, ComparativoVotacao.proposicao_id == Proposicao.id)
    )

    if resultado:
        stmt = stmt.where(ComparativoVotacao.resultado_camara == resultado.upper())

    stmt = stmt.order_by(ComparativoVotacao.data_geracao.desc()).limit(10_000)

    result = await db.execute(stmt)
    rows = result.all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "proposicao",
        "ementa",
        "temas",
        "resultado_camara",
        "voto_popular_sim",
        "voto_popular_nao",
        "voto_popular_abstencao",
        "votos_camara_sim",
        "votos_camara_nao",
        "alinhamento",
        "data_geracao",
    ])

    for row in rows:
        comp = row[0]  # ComparativoVotacao
        temas = _parse_temas(row.temas)
        data_str = comp.data_geracao.isoformat() if comp.data_geracao else ""
        writer.writerow([
            f"{row.tipo} {row.numero}/{row.ano}",
            (row.ementa or "")[:200],
            "; ".join(temas),
            comp.resultado_camara or "",
            comp.voto_popular_sim,
            comp.voto_popular_nao,
            comp.voto_popular_abstencao,
            comp.votos_camara_sim,
            comp.votos_camara_nao,
            round(comp.alinhamento, 4) if comp.alinhamento is not None else "",
            data_str,
        ])

    ts = datetime.now(timezone.utc).strftime("%Y%m%d")
    return _csv_response(buf, f"comparativos_{ts}.csv")
