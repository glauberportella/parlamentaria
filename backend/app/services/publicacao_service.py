"""Service for publication and distribution — RSS Feed and outbound Webhooks.

Handles RSS feed generation and webhook dispatch to external consumers
(parliamentarians, external systems).
"""

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Sequence

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.assinatura import AssinaturaRSS, AssinaturaWebhook
from app.config import settings
from app.exceptions import NotFoundException
from app.logging import get_logger

logger = get_logger(__name__)


class PublicacaoService:
    """Manages RSS subscriptions and outbound webhook dispatch."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # RSS Subscriptions
    # ------------------------------------------------------------------

    async def create_rss_subscription(
        self,
        nome: str,
        filtro_temas: list[str] | None = None,
        filtro_uf: str | None = None,
        email: str | None = None,
    ) -> AssinaturaRSS:
        """Create a new RSS feed subscription.

        Args:
            nome: Subscriber name.
            filtro_temas: Themes to filter the feed.
            filtro_uf: UF filter.
            email: Contact email.

        Returns:
            Created AssinaturaRSS with unique token.
        """
        token = uuid.uuid4().hex
        assinatura = AssinaturaRSS(
            nome=nome,
            email=email,
            token=token,
            filtro_temas=filtro_temas,
            filtro_uf=filtro_uf,
        )
        self.session.add(assinatura)
        await self.session.flush()
        await self.session.refresh(assinatura)
        logger.info("publicacao.rss.created", nome=nome, token=token)
        return assinatura

    async def get_rss_by_token(self, token: str) -> AssinaturaRSS | None:
        """Find an RSS subscription by token.

        Args:
            token: Unique subscription token.

        Returns:
            AssinaturaRSS or None.
        """
        stmt = select(AssinaturaRSS).where(
            AssinaturaRSS.token == token,
            AssinaturaRSS.ativo == True,  # noqa: E712
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_rss_by_id(self, assinatura_id: uuid.UUID) -> AssinaturaRSS:
        """Get an RSS subscription by ID.

        Args:
            assinatura_id: Subscription UUID.

        Returns:
            AssinaturaRSS.

        Raises:
            NotFoundException: If not found.
        """
        result = await self.session.get(AssinaturaRSS, assinatura_id)
        if result is None:
            raise NotFoundException(detail="Assinatura RSS não encontrada")
        return result

    async def delete_rss(self, assinatura_id: uuid.UUID) -> None:
        """Cancel an RSS subscription.

        Args:
            assinatura_id: Subscription UUID.

        Raises:
            NotFoundException: If not found.
        """
        assinatura = await self.get_rss_by_id(assinatura_id)
        await self.session.delete(assinatura)
        await self.session.flush()
        logger.info("publicacao.rss.deleted", id=str(assinatura_id))

    async def list_rss_subscriptions(self, active_only: bool = True) -> Sequence[AssinaturaRSS]:
        """List RSS subscriptions.

        Args:
            active_only: Only return active subscriptions.

        Returns:
            Sequence of AssinaturaRSS.
        """
        stmt = select(AssinaturaRSS)
        if active_only:
            stmt = stmt.where(AssinaturaRSS.ativo == True)  # noqa: E712
        result = await self.session.execute(stmt)
        return result.scalars().all()

    # ------------------------------------------------------------------
    # Webhook Subscriptions
    # ------------------------------------------------------------------

    async def create_webhook_subscription(
        self,
        nome: str,
        url: str,
        secret: str,
        eventos: list[str],
        filtro_temas: list[str] | None = None,
    ) -> AssinaturaWebhook:
        """Register a new outbound webhook subscription.

        Args:
            nome: Subscriber name.
            url: Callback URL (HTTPS).
            secret: HMAC secret for payload signing.
            eventos: Event types to subscribe to.
            filtro_temas: Theme filter.

        Returns:
            Created AssinaturaWebhook.
        """
        webhook = AssinaturaWebhook(
            nome=nome,
            url=url,
            secret=secret,
            eventos=eventos,
            filtro_temas=filtro_temas,
        )
        self.session.add(webhook)
        await self.session.flush()
        await self.session.refresh(webhook)
        logger.info("publicacao.webhook.created", nome=nome, url=url)
        return webhook

    async def get_webhook_by_id(self, webhook_id: uuid.UUID) -> AssinaturaWebhook:
        """Get a webhook subscription by ID.

        Args:
            webhook_id: Webhook UUID.

        Returns:
            AssinaturaWebhook.

        Raises:
            NotFoundException: If not found.
        """
        result = await self.session.get(AssinaturaWebhook, webhook_id)
        if result is None:
            raise NotFoundException(detail="Assinatura Webhook não encontrada")
        return result

    async def update_webhook(
        self, webhook_id: uuid.UUID, data: dict[str, Any]
    ) -> AssinaturaWebhook:
        """Update a webhook subscription.

        Args:
            webhook_id: Webhook UUID.
            data: Fields to update.

        Returns:
            Updated AssinaturaWebhook.

        Raises:
            NotFoundException: If not found.
        """
        webhook = await self.get_webhook_by_id(webhook_id)
        for key, value in data.items():
            if hasattr(webhook, key):
                setattr(webhook, key, value)
        await self.session.flush()
        await self.session.refresh(webhook)
        logger.info("publicacao.webhook.updated", id=str(webhook_id))
        return webhook

    async def delete_webhook(self, webhook_id: uuid.UUID) -> None:
        """Remove a webhook subscription.

        Args:
            webhook_id: Webhook UUID.

        Raises:
            NotFoundException: If not found.
        """
        webhook = await self.get_webhook_by_id(webhook_id)
        await self.session.delete(webhook)
        await self.session.flush()
        logger.info("publicacao.webhook.deleted", id=str(webhook_id))

    async def list_webhooks_for_event(self, evento: str) -> Sequence[AssinaturaWebhook]:
        """List active webhooks subscribed to a specific event type.

        Args:
            evento: Event type name (e.g., "voto_consolidado").

        Returns:
            Sequence of active webhooks listening for this event.
        """
        stmt = select(AssinaturaWebhook).where(
            AssinaturaWebhook.ativo == True,  # noqa: E712
        )
        result = await self.session.execute(stmt)
        webhooks = result.scalars().all()
        # Filter by event type (ARRAY contains — handled in Python for SQLite compat)
        return [wh for wh in webhooks if evento in (wh.eventos or [])]

    async def record_webhook_failure(self, webhook_id: uuid.UUID) -> None:
        """Record a webhook dispatch failure and apply circuit breaker.

        Increments consecutive failure count. Deactivates if threshold exceeded.

        Args:
            webhook_id: Webhook UUID.
        """
        webhook = await self.get_webhook_by_id(webhook_id)
        webhook.falhas_consecutivas = (webhook.falhas_consecutivas or 0) + 1
        if webhook.falhas_consecutivas >= settings.webhook_circuit_breaker_threshold:
            webhook.ativo = False
            logger.warning(
                "publicacao.webhook.circuit_breaker",
                id=str(webhook_id),
                nome=webhook.nome,
                failures=webhook.falhas_consecutivas,
            )
        await self.session.flush()

    async def record_webhook_success(self, webhook_id: uuid.UUID) -> None:
        """Record a successful webhook dispatch.

        Resets the consecutive failure counter.

        Args:
            webhook_id: Webhook UUID.
        """
        webhook = await self.get_webhook_by_id(webhook_id)
        webhook.falhas_consecutivas = 0
        webhook.ultimo_dispatch = datetime.now(timezone.utc)
        await self.session.flush()

    # ------------------------------------------------------------------
    # Webhook Dispatch
    # ------------------------------------------------------------------

    @staticmethod
    def sign_payload(payload: str, secret: str) -> str:
        """Sign a JSON payload with HMAC-SHA256.

        Args:
            payload: JSON string to sign.
            secret: HMAC secret.

        Returns:
            Hex-encoded HMAC signature.
        """
        return hmac.new(
            secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    async def dispatch_webhook(
        self, webhook: AssinaturaWebhook, payload: dict
    ) -> bool:
        """Dispatch a payload to a single webhook endpoint.

        Args:
            webhook: Webhook subscription to dispatch to.
            payload: Event payload dict.

        Returns:
            True if dispatch succeeded, False otherwise.
        """
        json_payload = json.dumps(payload, default=str, ensure_ascii=False)
        signature = self.sign_payload(json_payload, webhook.secret)

        try:
            async with httpx.AsyncClient(timeout=settings.webhook_dispatch_timeout) as client:
                response = await client.post(
                    webhook.url,
                    content=json_payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Signature": f"sha256={signature}",
                        "X-Parlamentaria-Event": payload.get("evento", "unknown"),
                    },
                )
                if response.status_code < 300:
                    await self.record_webhook_success(webhook.id)
                    logger.info(
                        "publicacao.webhook.dispatched",
                        webhook_id=str(webhook.id),
                        url=webhook.url,
                        status=response.status_code,
                    )
                    return True
                else:
                    logger.warning(
                        "publicacao.webhook.dispatch_failed",
                        webhook_id=str(webhook.id),
                        url=webhook.url,
                        status=response.status_code,
                    )
                    await self.record_webhook_failure(webhook.id)
                    return False
        except Exception as e:
            logger.error(
                "publicacao.webhook.dispatch_error",
                webhook_id=str(webhook.id),
                url=webhook.url,
                error=str(e),
            )
            await self.record_webhook_failure(webhook.id)
            return False

    async def dispatch_event(self, evento: str, payload: dict) -> dict:
        """Dispatch an event to all subscribed webhooks.

        Args:
            evento: Event type (e.g., "voto_consolidado").
            payload: Event payload.

        Returns:
            Dict with success and failure counts.
        """
        payload["evento"] = evento
        payload["timestamp"] = datetime.now(timezone.utc).isoformat()

        # Try premium webhook enrichment (adds IA analysis, per-UF data)
        enriched_payload = await self._try_enrich_payload(payload)

        webhooks = await self.list_webhooks_for_event(evento)
        stats = {"total": len(webhooks), "success": 0, "failed": 0}

        for webhook in webhooks:
            try:
                async with self.session.begin_nested():
                    ok = await self.dispatch_webhook(webhook, enriched_payload)
                if ok:
                    stats["success"] += 1
                else:
                    stats["failed"] += 1
            except Exception as e:
                logger.error(
                    "publicacao.event.dispatch_error",
                    webhook_id=str(webhook.id),
                    error=str(e),
                )
                stats["failed"] += 1

        logger.info("publicacao.event.dispatched", evento=evento, **stats)
        return stats

    async def _try_enrich_payload(self, payload: dict) -> dict:
        """Attempt premium webhook enrichment (ImportError-safe)."""
        try:
            from premium.billing.webhook_enrichment import enrich_webhook_payload
            return await enrich_webhook_payload(self.session, payload.copy())
        except ImportError:
            return payload
        except Exception:
            logger.debug("publicacao.webhook.enrich_skipped", exc_info=True)
            return payload
