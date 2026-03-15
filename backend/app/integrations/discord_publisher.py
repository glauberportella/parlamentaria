"""Discord publisher using httpx (Webhook embeds)."""

import httpx

from app.config import settings
from app.domain.social_post import TipoPostSocial
from app.integrations.social_publisher import (
    DiscordEmbed,
    PostMetrics,
    PublishResult,
    SocialPublisher,
)
from app.logging import get_logger

logger = get_logger(__name__)


class DiscordPublisher(SocialPublisher):
    """Publishes posts to Discord via Webhook embeds."""

    def _webhook_url_for(self, tipo: TipoPostSocial | None = None) -> str:
        """Select the appropriate webhook URL based on post type."""
        if tipo == TipoPostSocial.RESUMO_SEMANAL:
            return settings.discord_webhook_resumo or settings.discord_webhook_geral
        if tipo == TipoPostSocial.EXPLICATIVO_EDUCATIVO:
            return settings.discord_webhook_educativo or settings.discord_webhook_geral
        if tipo in (TipoPostSocial.COMPARATIVO, TipoPostSocial.VOTACAO_RELEVANTE):
            return settings.discord_webhook_votacoes or settings.discord_webhook_geral
        return settings.discord_webhook_geral

    async def publish_text(self, text: str) -> PublishResult:
        """Publish a text message to Discord."""
        webhook_url = self._webhook_url_for()
        if not webhook_url:
            return PublishResult(success=False, error="Nenhum webhook Discord configurado.")

        async with httpx.AsyncClient(timeout=15) as client:
            try:
                resp = await client.post(
                    webhook_url,
                    json={"content": text, "username": "Parlamentaria Bot"},
                    params={"wait": "true"},
                )
                resp.raise_for_status()
                data = resp.json()
                return PublishResult(
                    success=True,
                    post_id=data.get("id"),
                )
            except httpx.HTTPError as e:
                logger.error("discord.publish_text.error", error=str(e))
                return PublishResult(success=False, error="Falha ao publicar no Discord.")

    async def publish_with_image(self, text: str, image_path: str) -> PublishResult:
        """Publish a message with image attachment to Discord."""
        webhook_url = self._webhook_url_for()
        if not webhook_url:
            return PublishResult(success=False, error="Nenhum webhook Discord configurado.")

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                with open(image_path, "rb") as f:
                    resp = await client.post(
                        webhook_url,
                        data={
                            "payload_json": '{"content": ' + f'"{text}"' + ', "username": "Parlamentaria Bot"}',
                        },
                        files={"file": ("image.png", f, "image/png")},
                        params={"wait": "true"},
                    )
                resp.raise_for_status()
                data = resp.json()
                return PublishResult(
                    success=True,
                    post_id=data.get("id"),
                )
            except (httpx.HTTPError, OSError) as e:
                logger.error("discord.publish_with_image.error", error=str(e))
                return PublishResult(success=False, error="Falha ao publicar no Discord.")

    async def publish_embed(
        self,
        embed: DiscordEmbed,
        tipo: TipoPostSocial | None = None,
    ) -> PublishResult:
        """Publish a rich embed message to Discord."""
        webhook_url = self._webhook_url_for(tipo)
        if not webhook_url:
            return PublishResult(success=False, error="Nenhum webhook Discord configurado.")

        embed_dict: dict = {
            "title": embed.title,
            "description": embed.description,
            "color": embed.color,
            "footer": {"text": embed.footer_text},
        }
        if embed.fields:
            embed_dict["fields"] = embed.fields
        if embed.image_url:
            embed_dict["image"] = {"url": embed.image_url}
        if embed.timestamp:
            embed_dict["timestamp"] = embed.timestamp

        payload = {
            "username": "Parlamentaria Bot",
            "embeds": [embed_dict],
        }

        async with httpx.AsyncClient(timeout=15) as client:
            try:
                resp = await client.post(
                    webhook_url,
                    json=payload,
                    params={"wait": "true"},
                )
                resp.raise_for_status()
                data = resp.json()
                return PublishResult(success=True, post_id=data.get("id"))
            except httpx.HTTPError as e:
                logger.error("discord.publish_embed.error", error=str(e))
                return PublishResult(success=False, error="Falha ao publicar no Discord.")

    async def delete_post(self, post_id: str) -> bool:
        """Discord webhooks don't easily support deletion."""
        logger.warning("discord.delete.not_supported", post_id=post_id)
        return False

    async def get_metrics(self, post_id: str) -> PostMetrics:
        """Discord webhooks don't provide metrics."""
        return PostMetrics()
