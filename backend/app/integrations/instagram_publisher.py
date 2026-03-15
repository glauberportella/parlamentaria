"""Instagram publisher using httpx (Graph API — container-based publishing)."""

import asyncio

import httpx

from app.config import settings
from app.integrations.social_publisher import PostMetrics, PublishResult, SocialPublisher
from app.logging import get_logger

logger = get_logger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"


class InstagramPublisher(SocialPublisher):
    """Publishes posts to Instagram Business via Graph API.

    Instagram requires images to be accessible via public URL.
    The image_path must be either a public URL or a path that is
    served publicly via SOCIAL_IMAGES_PUBLIC_URL.
    """

    def __init__(self) -> None:
        self._user_id = settings.instagram_user_id
        self._token = settings.instagram_access_token
        self._public_url_base = settings.social_images_public_url

    def _to_public_url(self, image_path: str) -> str:
        """Convert a local path to a public URL for Instagram."""
        if image_path.startswith("http"):
            return image_path
        filename = image_path.rsplit("/", maxsplit=1)[-1]
        return f"{self._public_url_base}/{filename}"

    async def publish_text(self, text: str) -> PublishResult:
        """Instagram does not support text-only posts."""
        return PublishResult(
            success=False,
            error="Instagram requer imagem para publicação.",
        )

    async def publish_with_image(self, text: str, image_path: str) -> PublishResult:
        """Publish an image post to Instagram (container-based flow)."""
        image_url = self._to_public_url(image_path)

        async with httpx.AsyncClient(timeout=60) as client:
            try:
                # Step 1: Create media container
                create_url = f"{GRAPH_API_BASE}/{self._user_id}/media"
                resp = await client.post(
                    create_url,
                    data={
                        "image_url": image_url,
                        "caption": text,
                        "access_token": self._token,
                    },
                )
                resp.raise_for_status()
                container_id = resp.json().get("id")

                # Step 2: Wait for processing (poll status)
                for _ in range(10):
                    await asyncio.sleep(2)
                    status_resp = await client.get(
                        f"{GRAPH_API_BASE}/{container_id}",
                        params={
                            "fields": "status_code",
                            "access_token": self._token,
                        },
                    )
                    status_data = status_resp.json()
                    if status_data.get("status_code") == "FINISHED":
                        break

                # Step 3: Publish the container
                publish_url = f"{GRAPH_API_BASE}/{self._user_id}/media_publish"
                pub_resp = await client.post(
                    publish_url,
                    data={
                        "creation_id": container_id,
                        "access_token": self._token,
                    },
                )
                pub_resp.raise_for_status()
                media_id = pub_resp.json().get("id", "")

                return PublishResult(
                    success=True,
                    post_id=media_id,
                    url=f"https://instagram.com/p/{media_id}",
                )
            except httpx.HTTPError as e:
                logger.error("instagram.publish.error", error=str(e))
                return PublishResult(
                    success=False,
                    error="Falha ao publicar no Instagram.",
                )

    async def delete_post(self, post_id: str) -> bool:
        """Instagram does not support deletion via API for most post types."""
        logger.warning("instagram.delete.not_supported", post_id=post_id)
        return False

    async def get_metrics(self, post_id: str) -> PostMetrics:
        """Fetch Instagram media insights."""
        url = f"{GRAPH_API_BASE}/{post_id}/insights"
        params = {
            "metric": "impressions,reach,likes,comments,shares",
            "access_token": self._token,
        }
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json().get("data", [])
                metrics = {item["name"]: item["values"][0]["value"] for item in data}
                return PostMetrics(
                    likes=metrics.get("likes", 0),
                    shares=metrics.get("shares", 0),
                    comments=metrics.get("comments", 0),
                    impressions=metrics.get("impressions", 0),
                )
            except (httpx.HTTPError, KeyError, IndexError) as e:
                logger.warning("instagram.metrics.error", post_id=post_id, error=str(e))
        return PostMetrics()
