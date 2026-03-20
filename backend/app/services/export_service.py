"""Export service — orchestrates async export job lifecycle."""

import csv
import io
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.domain.comparativo import ComparativoVotacao
from app.domain.eleitor import Eleitor
from app.domain.export_job import ExportJob, ExportJobStatus, ExportJobType
from app.domain.proposicao import Proposicao
from app.domain.voto_popular import VotoPopular
from app.logging import get_logger
from app.repositories.export_job_repo import ExportJobRepository

logger = get_logger(__name__)

# Row limits matching existing plan tiers
_FREE_EXPORT_LIMIT = 100
_PRO_EXPORT_LIMIT = 50_000

try:
    from premium.billing.gabinete_gate import PLAN_HIERARCHY
    _has_premium = True
except ImportError:
    PLAN_HIERARCHY = {}
    _has_premium = False


def _export_row_limit(user_plan: str | None) -> int:
    """Return max rows based on plan tier."""
    if not _has_premium:
        return _PRO_EXPORT_LIMIT
    plan = user_plan or "gabinete_free"
    level = PLAN_HIERARCHY.get(plan, 0)
    return _PRO_EXPORT_LIMIT if level >= 1 else _FREE_EXPORT_LIMIT


def _ensure_export_dir() -> Path:
    """Create export directory if it doesn't exist."""
    export_path = Path(settings.export_dir)
    export_path.mkdir(parents=True, exist_ok=True)
    return export_path


class ExportService:
    """Manages export job creation and CSV generation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ExportJobRepository(session)

    async def create_job(
        self,
        user_id: str,
        user_plan: str | None,
        tipo: ExportJobType,
        filtros: dict | None = None,
    ) -> ExportJob:
        """Create a new export job and return it.

        Raises ValueError if user has too many active jobs.
        """
        active = await self.repo.count_active_by_user(user_id)
        if active >= settings.export_max_concurrent_per_user:
            raise ValueError(
                f"Limite de {settings.export_max_concurrent_per_user} "
                "exportações simultâneas atingido. Aguarde a conclusão das anteriores."
            )

        row_limit = _export_row_limit(user_plan)
        job_filtros = dict(filtros or {})
        job_filtros["_row_limit"] = row_limit

        job = ExportJob(
            parlamentar_user_id=user_id,
            tipo=tipo,
            status=ExportJobStatus.PENDING,
            filtros=job_filtros,
        )
        await self.repo.create(job)
        await self.session.commit()
        return job

    async def list_jobs(
        self, user_id: str, limit: int = 20, offset: int = 0
    ) -> list[ExportJob]:
        """List user's export jobs."""
        return await self.repo.list_by_user(user_id, limit, offset)

    async def get_job(self, job_id: UUID, user_id: str) -> ExportJob | None:
        """Get a job only if owned by user."""
        job = await self.repo.get_by_id(job_id)
        if job and job.parlamentar_user_id == user_id:
            return job
        return None

    async def delete_job(self, job_id: UUID, user_id: str) -> bool:
        """Cancel/delete a job. Removes file if exists."""
        job = await self.repo.get_by_id(job_id)
        if not job or job.parlamentar_user_id != user_id:
            return False

        # Remove file from disk
        if job.file_name:
            file_path = Path(settings.export_dir) / job.file_name
            if file_path.exists():
                file_path.unlink(missing_ok=True)

        await self.session.delete(job)
        await self.session.commit()
        return True

    async def process_job(self, job_id: UUID) -> None:
        """Execute the export job — called by Celery task.

        Generates CSV, saves to disk, updates status.
        """
        job = await self.repo.get_by_id(job_id)
        if not job or job.status != ExportJobStatus.PENDING:
            logger.warning("export.job.skip", job_id=str(job_id), reason="not_pending")
            return

        now = datetime.now(timezone.utc)
        await self.repo.update_status(
            job_id, ExportJobStatus.PROCESSING, started_at=now
        )
        await self.session.commit()

        try:
            filtros = job.filtros or {}
            row_limit = filtros.pop("_row_limit", _PRO_EXPORT_LIMIT)

            if job.tipo == ExportJobType.VOTOS:
                total, file_name = await self._generate_votos_csv(
                    job_id, filtros, row_limit
                )
            elif job.tipo == ExportJobType.COMPARATIVOS:
                total, file_name = await self._generate_comparativos_csv(
                    job_id, filtros, row_limit
                )
            else:
                raise ValueError(f"Tipo de export desconhecido: {job.tipo}")

            file_path = _ensure_export_dir() / file_name
            file_size = file_path.stat().st_size

            expires_at = now + timedelta(days=settings.export_expiry_days)

            await self.repo.update_status(
                job_id,
                ExportJobStatus.COMPLETED,
                completed_at=datetime.now(timezone.utc),
                total_rows=total,
                file_name=file_name,
                file_size_bytes=file_size,
                expires_at=expires_at,
            )
            await self.session.commit()

            logger.info(
                "export.job.completed",
                job_id=str(job_id),
                rows=total,
                size_bytes=file_size,
            )

        except Exception as exc:
            logger.error("export.job.failed", job_id=str(job_id), error=str(exc))
            await self.repo.update_status(
                job_id,
                ExportJobStatus.FAILED,
                completed_at=datetime.now(timezone.utc),
                error_message=str(exc)[:500],
            )
            await self.session.commit()

    async def _generate_votos_csv(
        self, job_id: UUID, filtros: dict, row_limit: int
    ) -> tuple[int, str]:
        """Generate votos CSV and save to disk. Returns (row_count, filename)."""
        from app.domain.voto_popular import TipoVoto

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

        if filtros.get("proposicao_id"):
            stmt = stmt.where(VotoPopular.proposicao_id == int(filtros["proposicao_id"]))
        if filtros.get("tipo_voto"):
            tipo_v = filtros["tipo_voto"].upper()
            if tipo_v in ("OFICIAL", "OPINIAO"):
                stmt = stmt.where(VotoPopular.tipo_voto == TipoVoto(tipo_v))

        stmt = stmt.order_by(VotoPopular.data_voto.desc()).limit(row_limit)
        result = await self.session.execute(stmt)
        rows = result.all()

        file_name = f"votos_{job_id}.csv"
        file_path = _ensure_export_dir() / file_name

        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "tipo", "numero", "ano", "ementa",
                "voto", "tipo_voto", "uf_eleitor", "data_voto",
            ])
            for row in rows:
                writer.writerow([
                    row.tipo or "",
                    row.numero or "",
                    row.ano or "",
                    (row.ementa or "")[:200],
                    row.voto or "",
                    row.tipo_voto or "",
                    row.uf or "",
                    row.data_voto.isoformat() if row.data_voto else "",
                ])

        return len(rows), file_name

    async def _generate_comparativos_csv(
        self, job_id: UUID, filtros: dict, row_limit: int
    ) -> tuple[int, str]:
        """Generate comparativos CSV and save to disk."""
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

        if filtros.get("resultado"):
            stmt = stmt.where(
                ComparativoVotacao.resultado_camara == filtros["resultado"].upper()
            )

        limit = min(row_limit, 10_000)
        stmt = stmt.order_by(ComparativoVotacao.data_geracao.desc()).limit(limit)

        result = await self.session.execute(stmt)
        rows = result.all()

        file_name = f"comparativos_{job_id}.csv"
        file_path = _ensure_export_dir() / file_name

        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "proposicao", "ementa", "temas", "resultado_camara",
                "voto_popular_sim", "voto_popular_nao", "voto_popular_abstencao",
                "votos_camara_sim", "votos_camara_nao", "alinhamento", "data_geracao",
            ])
            for row in rows:
                comp = row[0]
                temas = self._parse_temas(row.temas)
                writer.writerow([
                    f"{row.tipo} {row.numero}/{row.ano}",
                    (row.ementa or "")[:200],
                    "; ".join(temas),
                    comp.resultado_camara or "",
                    comp.voto_popular_sim or 0,
                    comp.voto_popular_nao or 0,
                    comp.voto_popular_abstencao or 0,
                    comp.votos_camara_sim or 0,
                    comp.votos_camara_nao or 0,
                    f"{comp.alinhamento:.2f}" if comp.alinhamento else "",
                    comp.data_geracao.isoformat() if comp.data_geracao else "",
                ])

        return len(rows), file_name

    @staticmethod
    def _parse_temas(temas_raw) -> list[str]:
        if temas_raw is None:
            return []
        if isinstance(temas_raw, list):
            return temas_raw
        if isinstance(temas_raw, str):
            try:
                parsed = json.loads(temas_raw)
                return parsed if isinstance(parsed, list) else []
            except (json.JSONDecodeError, TypeError):
                return []
        return []

    async def cleanup_expired(self) -> dict:
        """Remove expired export files and mark jobs as EXPIRED.

        Returns stats dict with counts.
        """
        expired_jobs = await self.repo.get_expired_completed()
        stats = {"expired": 0, "files_removed": 0}

        for job in expired_jobs:
            if job.file_name:
                file_path = Path(settings.export_dir) / job.file_name
                if file_path.exists():
                    file_path.unlink(missing_ok=True)
                    stats["files_removed"] += 1

            await self.repo.update_status(job.id, ExportJobStatus.EXPIRED)
            stats["expired"] += 1

        if stats["expired"] > 0:
            await self.session.commit()

        return stats
