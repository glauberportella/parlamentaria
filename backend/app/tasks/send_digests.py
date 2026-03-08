"""Celery tasks: periodic engagement digests (daily + weekly).

Sends personalised digest notifications to voters based on their
``frequencia_notificacao`` preference. Orchestrates the DigestService
for content generation and the TelegramAdapter for delivery.
"""

import asyncio

from app.tasks.celery_app import celery_app
from app.tasks.helpers import get_async_session
from app.logging import get_logger

logger = get_logger(__name__)


async def _get_telegram_send_fn():
    """Create a send function using the TelegramAdapter.

    Returns:
        Async callable(chat_id, text) or None if Telegram is not configured.
    """
    from app.config import settings

    if not settings.telegram_bot_token:
        logger.warning("digest.telegram_not_configured")
        return None

    from channels.telegram.bot import TelegramAdapter

    adapter = TelegramAdapter(token=settings.telegram_bot_token)

    async def send(chat_id: str, text: str) -> None:
        await adapter.send_message(chat_id, text)

    return send


@celery_app.task(name="app.tasks.send_digests.send_weekly_digest_task")
def send_weekly_digest_task() -> dict:
    """Send weekly digest to all voters with SEMANAL frequency.

    Scheduled for Monday mornings. Gathers a 7-day summary of:
    - New propositions matching voter interests
    - Most-voted propositions on the platform
    - Comparativo results (popular vs parliamentary)
    - Upcoming plenary events
    - Platform engagement stats

    Returns:
        Dict with send statistics.
    """
    logger.info("task.weekly_digest.start")

    async def _run() -> dict:
        from app.domain.eleitor import FrequenciaNotificacao
        from app.services.digest_service import DigestService

        send_fn = await _get_telegram_send_fn()

        async with get_async_session() as session:
            service = DigestService(session)
            stats = await service.send_digests(
                frequencia=FrequenciaNotificacao.SEMANAL,
                send_fn=send_fn,
            )
            return stats

    try:
        result = asyncio.get_event_loop().run_until_complete(_run())
    except RuntimeError:
        result = asyncio.run(_run())

    logger.info("task.weekly_digest.complete", **result)
    return result


@celery_app.task(name="app.tasks.send_digests.send_daily_digest_task")
def send_daily_digest_task() -> dict:
    """Send daily digest to voters with DIARIA or IMEDIATA frequency.

    Scheduled every morning after sync. Gathers a 1-day summary.
    Voters with IMEDIATA frequency get this in addition to real-time alerts.

    Returns:
        Dict with send statistics.
    """
    logger.info("task.daily_digest.start")

    async def _run() -> dict:
        from app.domain.eleitor import FrequenciaNotificacao
        from app.services.digest_service import DigestService

        send_fn = await _get_telegram_send_fn()

        async with get_async_session() as session:
            service = DigestService(session)
            stats = await service.send_digests(
                frequencia=FrequenciaNotificacao.DIARIA,
                send_fn=send_fn,
            )
            return stats

    try:
        result = asyncio.get_event_loop().run_until_complete(_run())
    except RuntimeError:
        result = asyncio.run(_run())

    logger.info("task.daily_digest.complete", **result)
    return result
