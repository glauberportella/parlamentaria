"""Export endpoints for the parlamentar dashboard.

Provides CSV export for votos and comparativos data.
Sync endpoints for quick small exports + async job system for large exports.
"""

import csv
import io
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_db
from app.domain.comparativo import ComparativoVotacao
from app.domain.export_job import ExportJob, ExportJobStatus, ExportJobType
from app.domain.proposicao import Proposicao
from app.domain.voto_popular import VotoPopular
from app.domain.eleitor import Eleitor
from app.logging import get_logger
from app.routers.parlamentar.auth import get_current_parlamentar_user
from app.schemas.parlamentar import ParlamentarUserResponse

# Premium plan gate — only enforced when parlamentaria-premium is installed
try:
    from premium.billing.gabinete_gate import require_gabinete_plan, PLAN_HIERARCHY

    _has_premium = True
except ImportError:
    PLAN_HIERARCHY = {}
    _has_premium = False

# Row limits per plan tier (Free=100, Pro/Enterprise=50000)
_FREE_EXPORT_LIMIT = 100
_PRO_EXPORT_LIMIT = 50_000

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


def _export_row_limit(user: ParlamentarUserResponse) -> int:
    """Return export row limit based on user plan tier."""
    if not _has_premium:
        return _PRO_EXPORT_LIMIT  # no premium installed → no limit
    user_plan = getattr(user, "plano", "gabinete_free") or "gabinete_free"
    level = PLAN_HIERARCHY.get(user_plan, 0)
    return _PRO_EXPORT_LIMIT if level >= 1 else _FREE_EXPORT_LIMIT


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
    current_user: ParlamentarUserResponse = Depends(get_current_parlamentar_user),
) -> StreamingResponse:
    """Export votos populares as CSV.

    Free plan: limited to 100 rows. Pro+: up to 50,000 rows.
    Columns: proposicao_tipo, proposicao_numero, proposicao_ano, ementa, voto,
    tipo_voto, uf_eleitor, data_voto.
    Electors are anonymised (only UF is exported).
    """
    row_limit = _export_row_limit(current_user)
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

    stmt = stmt.order_by(VotoPopular.data_voto.desc()).limit(row_limit)

    result = await db.execute(stmt)
    rows = result.all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    header = [
        "tipo",
        "numero",
        "ano",
        "ementa",
        "voto",
        "tipo_voto",
        "uf_eleitor",
        "data_voto",
    ]
    if row_limit <= _FREE_EXPORT_LIMIT:
        header.append("limite_plano_gratuito")
    writer.writerow(header)
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
    current_user: ParlamentarUserResponse = Depends(get_current_parlamentar_user),
) -> StreamingResponse:
    """Export comparativos as CSV.

    Free plan: limited to 100 rows. Pro+: up to 10,000 rows.
    Columns: proposicao, ementa, temas, resultado_camara,
    voto_pop_sim, voto_pop_nao, voto_pop_abstencao,
    votos_camara_sim, votos_camara_nao, alinhamento, data.
    """
    row_limit = min(_export_row_limit(current_user), 10_000)
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

    stmt = stmt.order_by(ComparativoVotacao.data_geracao.desc()).limit(row_limit)

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


# ──────────────────────────────────────────────────────────
#  Async export job system — Pydantic schemas
# ──────────────────────────────────────────────────────────


class CreateExportJobRequest(BaseModel):
    """Request to create an async export job."""

    tipo: str  # "VOTOS" or "COMPARATIVOS"
    filtros: dict | None = None


class ExportJobResponse(BaseModel):
    """Response for a single export job."""

    id: str
    tipo: str
    status: str
    filtros: dict | None = None
    total_rows: int | None = None
    file_name: str | None = None
    file_size_bytes: int | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    expires_at: datetime | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_job(cls, job: ExportJob) -> "ExportJobResponse":
        return cls(
            id=str(job.id),
            tipo=job.tipo.value if job.tipo else "",
            status=job.status.value if job.status else "",
            filtros=job.filtros,
            total_rows=job.total_rows,
            file_name=job.file_name,
            file_size_bytes=job.file_size_bytes,
            error_message=job.error_message,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            expires_at=job.expires_at,
        )


class ExportJobListResponse(BaseModel):
    """Paginated list of export jobs."""

    jobs: list[ExportJobResponse]
    total: int


# ──────────────────────────────────────────────────────────
#  Async export job endpoints
# ──────────────────────────────────────────────────────────


@router.post("/jobs", response_model=ExportJobResponse, status_code=201)
async def create_export_job(
    body: CreateExportJobRequest,
    db: AsyncSession = Depends(get_db),
    current_user: ParlamentarUserResponse = Depends(get_current_parlamentar_user),
) -> ExportJobResponse:
    """Create an async export job. Returns immediately.

    The export is processed in background by Celery.
    When complete, the file can be downloaded and an email notification is sent.
    """
    from app.services.export_service import ExportService

    tipo_str = body.tipo.upper()
    if tipo_str not in ("VOTOS", "COMPARATIVOS"):
        raise HTTPException(status_code=422, detail="tipo deve ser VOTOS ou COMPARATIVOS")

    tipo = ExportJobType(tipo_str)
    user_plan = getattr(current_user, "plano", "gabinete_free")

    service = ExportService(db)
    try:
        job = await service.create_job(
            user_id=current_user.id,
            user_plan=user_plan,
            tipo=tipo,
            filtros=body.filtros,
        )
    except ValueError as e:
        raise HTTPException(status_code=429, detail=str(e))

    # Dispatch Celery task
    from app.tasks.export_tasks import process_export_job_task

    process_export_job_task.delay(str(job.id))

    logger.info("export.job.created", job_id=str(job.id), tipo=tipo_str)
    return ExportJobResponse.from_job(job)


@router.get("/jobs", response_model=ExportJobListResponse)
async def list_export_jobs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: ParlamentarUserResponse = Depends(get_current_parlamentar_user),
) -> ExportJobListResponse:
    """List the current user's export jobs."""
    from app.services.export_service import ExportService

    service = ExportService(db)
    jobs = await service.list_jobs(current_user.id, limit, offset)

    return ExportJobListResponse(
        jobs=[ExportJobResponse.from_job(j) for j in jobs],
        total=len(jobs),
    )


@router.get("/jobs/{job_id}", response_model=ExportJobResponse)
async def get_export_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: ParlamentarUserResponse = Depends(get_current_parlamentar_user),
) -> ExportJobResponse:
    """Get status of a specific export job."""
    from app.services.export_service import ExportService

    service = ExportService(db)
    job = await service.get_job(UUID(job_id), current_user.id)
    if not job:
        raise HTTPException(status_code=404, detail="Exportação não encontrada")
    return ExportJobResponse.from_job(job)


@router.get("/jobs/{job_id}/download")
async def download_export_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: ParlamentarUserResponse = Depends(get_current_parlamentar_user),
) -> FileResponse:
    """Download the CSV file for a completed export job."""
    from app.services.export_service import ExportService

    service = ExportService(db)
    job = await service.get_job(UUID(job_id), current_user.id)

    if not job:
        raise HTTPException(status_code=404, detail="Exportação não encontrada")

    if job.status != ExportJobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Exportação ainda não concluída")

    if not job.file_name:
        raise HTTPException(status_code=404, detail="Arquivo não disponível")

    file_path = Path(settings.export_dir) / job.file_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo expirado ou removido")

    # Security: ensure file_path is within export_dir (prevent path traversal)
    resolved = file_path.resolve()
    export_dir_resolved = Path(settings.export_dir).resolve()
    if not str(resolved).startswith(str(export_dir_resolved)):
        raise HTTPException(status_code=403, detail="Acesso negado")

    return FileResponse(
        path=str(resolved),
        media_type="text/csv; charset=utf-8",
        filename=job.file_name,
    )


@router.delete("/jobs/{job_id}", status_code=204)
async def delete_export_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: ParlamentarUserResponse = Depends(get_current_parlamentar_user),
) -> None:
    """Cancel/delete an export job and its file."""
    from app.services.export_service import ExportService

    service = ExportService(db)
    deleted = await service.delete_job(UUID(job_id), current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Exportação não encontrada")
