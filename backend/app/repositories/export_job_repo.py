"""Repository for ExportJob — async export job management."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.export_job import ExportJob, ExportJobStatus


class ExportJobRepository:
    """Data access for export jobs."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, job: ExportJob) -> ExportJob:
        """Persist a new export job."""
        self.session.add(job)
        await self.session.flush()
        return job

    async def get_by_id(self, job_id: UUID) -> ExportJob | None:
        """Get export job by ID."""
        return await self.session.get(ExportJob, job_id)

    async def list_by_user(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ExportJob]:
        """List export jobs for a user, newest first."""
        stmt = (
            select(ExportJob)
            .where(ExportJob.parlamentar_user_id == user_id)
            .order_by(ExportJob.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_active_by_user(self, user_id: str) -> int:
        """Count pending/processing jobs for a user (concurrency limit)."""
        stmt = (
            select(func.count())
            .select_from(ExportJob)
            .where(
                ExportJob.parlamentar_user_id == user_id,
                ExportJob.status.in_([
                    ExportJobStatus.PENDING,
                    ExportJobStatus.PROCESSING,
                ]),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def update_status(
        self,
        job_id: UUID,
        status: ExportJobStatus,
        **kwargs,
    ) -> None:
        """Update job status and optional fields."""
        values = {"status": status, **kwargs}
        stmt = update(ExportJob).where(ExportJob.id == job_id).values(**values)
        await self.session.execute(stmt)

    async def get_expired_completed(self) -> list[ExportJob]:
        """Find completed jobs whose files have expired."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(ExportJob)
            .where(
                ExportJob.status == ExportJobStatus.COMPLETED,
                ExportJob.expires_at.isnot(None),
                ExportJob.expires_at < now,
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
