"""Celery tasks for async export job processing and cleanup."""

import asyncio

from app.tasks.celery_app import celery_app
from app.tasks.helpers import get_async_session
from app.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(
    name="app.tasks.export_tasks.process_export_job_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=120,
    max_retries=2,
    retry_jitter=True,
)
def process_export_job_task(job_id: str) -> dict:
    """Process a single export job: generate CSV and save to disk.

    Args:
        job_id: UUID string of the ExportJob.

    Returns:
        Dict with processing result.
    """
    logger.info("task.export.start", job_id=job_id)

    async def _run() -> dict:
        from uuid import UUID

        from app.services.export_service import ExportService

        async with get_async_session() as session:
            service = ExportService(session)
            await service.process_job(UUID(job_id))

            # Send email notification after successful completion
            from app.domain.export_job import ExportJobStatus
            from app.repositories.export_job_repo import ExportJobRepository

            repo = ExportJobRepository(session)
            job = await repo.get_by_id(UUID(job_id))

            if job and job.status == ExportJobStatus.COMPLETED and not job.notificado_email:
                await _send_export_email(session, job)
                await repo.update_status(UUID(job_id), job.status, notificado_email=True)
                await session.commit()

        return {"job_id": job_id, "status": "processed"}

    result = asyncio.run(_run())
    logger.info("task.export.done", job_id=job_id)
    return result


@celery_app.task(
    name="app.tasks.export_tasks.cleanup_expired_exports_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=2,
)
def cleanup_expired_exports_task() -> dict:
    """Remove expired export files from disk and mark jobs as EXPIRED.

    Runs daily via Celery Beat.
    """
    logger.info("task.export.cleanup.start")

    async def _run() -> dict:
        from app.services.export_service import ExportService

        async with get_async_session() as session:
            service = ExportService(session)
            stats = await service.cleanup_expired()

        return stats

    result = asyncio.run(_run())
    logger.info("task.export.cleanup.done", **result)
    return result


async def _send_export_email(session, job) -> None:
    """Send email notification when export completes.

    Uses Resend (already configured in core). Fails silently if not configured.
    """
    from app.config import settings
    from app.domain.parlamentar_user import ParlamentarUser

    if not settings.resend_api_key:
        logger.debug("export.email.skip", reason="resend_not_configured")
        return

    # Get user email
    from sqlalchemy import select

    result = await session.execute(
        select(ParlamentarUser.email, ParlamentarUser.nome)
        .where(ParlamentarUser.id == job.parlamentar_user_id)
    )
    user = result.first()
    if not user or not user.email:
        return

    tipo_label = "Votos Populares" if job.tipo.value == "VOTOS" else "Comparativos"
    rows_label = f"{job.total_rows:,}" if job.total_rows else "N/A"
    download_url = f"{settings.dashboard_url}/exportacoes"

    html = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #1a73e8;">Parlamentaria</h2>
        <p>Olá, <strong>{user.nome or 'Parlamentar'}</strong>!</p>
        <p>Sua exportação de <strong>{tipo_label}</strong> foi concluída com sucesso.</p>
        <table style="border-collapse: collapse; margin: 16px 0;">
            <tr><td style="padding: 4px 12px; color: #666;">Registros:</td><td style="padding: 4px 12px;"><strong>{rows_label}</strong></td></tr>
            <tr><td style="padding: 4px 12px; color: #666;">Formato:</td><td style="padding: 4px 12px;">CSV</td></tr>
            <tr><td style="padding: 4px 12px; color: #666;">Disponível por:</td><td style="padding: 4px 12px;">{settings.export_expiry_days} dias</td></tr>
        </table>
        <p>
            <a href="{download_url}"
               style="display: inline-block; padding: 12px 24px; background: #1a73e8; color: white; text-decoration: none; border-radius: 6px;">
                Baixar Exportação
            </a>
        </p>
        <p style="color: #888; font-size: 12px; margin-top: 24px;">
            Este é um email automático da Parlamentaria. Não responda.
        </p>
    </div>
    """

    try:
        import resend

        resend.api_key = settings.resend_api_key
        resend.Emails.send({
            "from": settings.email_from,
            "to": [user.email],
            "subject": f"Parlamentaria — Exportação de {tipo_label} pronta",
            "html": html,
        })
        logger.info("export.email.sent", to=user.email, job_id=str(job.id))
    except Exception:
        logger.error("export.email.failed", to=user.email, job_id=str(job.id))
