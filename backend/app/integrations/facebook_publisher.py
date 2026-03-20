"""Facebook publisher using httpx (Graph API)."""

import httpx

from app.config import settings
from app.integrations.social_publisher import PostMetrics, PublishResult, SocialPublisher
from app.logging import get_logger

logger = get_logger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"


class FacebookPublisher(SocialPublisher):
    """Publishes posts to a Facebook Page via Graph API."""

    def __init__(self) -> None:
        self._page_id = settings.facebook_page_id
        self._token = settings.facebook_page_access_token

    async def publish_text(self, text: str) -> PublishResult:
        """Publish a text-only post to the Facebook Page."""
        url = f"{GRAPH_API_BASE}/{self._page_id}/feed"
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.post(
                    url,
                    data={"message": text, "access_token": self._token},
                )
                resp.raise_for_status()
                data = resp.json()
                post_id = data.get("id", "")
                return PublishResult(
                    success=True,
                    post_id=post_id,
                    url=f"https://facebook.com/{post_id}",
                )
            except httpx.HTTPError as e:
                logger.error("facebook.publish_text.error", error=str(e))
                return PublishResult(success=False, error="Falha ao publicar no Facebook.")

    async def publish_with_image(self, text: str, image_path: str) -> PublishResult:
        """Publish a post with image to the Facebook Page."""
        url = f"{GRAPH_API_BASE}/{self._page_id}/photos"
        async with httpx.AsyncClient(timeout=60) as client:
            try:
                with open(image_path, "rb") as f:
                    resp = await client.post(
                        url,
                        data={"caption": text, "access_token": self._token},
                        files={"source": ("image.png", f, "image/png")},
                    )
                resp.raise_for_status()
                data = resp.json()
                post_id = data.get("post_id", data.get("id", ""))
                return PublishResult(
                    success=True,
                    post_id=post_id,
                    url=f"https://facebook.com/{post_id}",
                )
            except (httpx.HTTPError, OSError) as e:
                logger.error("facebook.publish_with_image.error", error=str(e))
                return PublishResult(success=False, error="Falha ao publicar no Facebook.")

    async def delete_post(self, post_id: str) -> bool:
        """Delete a Facebook post."""
        url = f"{GRAPH_API_BASE}/{post_id}"
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                resp = await client.delete(
                    url, params={"access_token": self._token}
                )
                resp.raise_for_status()
                return True
            except httpx.HTTPError as e:
                logger.error("facebook.delete.error", post_id=post_id, error=str(e))
                return False

    async def get_metrics(self, post_id: str) -> PostMetrics:
        """Fetch Facebook post metrics."""
        url = f"{GRAPH_API_BASE}/{post_id}"
        params = {
            "fields": "likes.summary(true),shares,comments.summary(true)",
            "access_token": self._token,
        }
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                return PostMetrics(
                    likes=data.get("likes", {}).get("summary", {}).get("total_count", 0),
                    shares=data.get("shares", {}).get("count", 0),
                    comments=data.get("comments", {}).get("summary", {}).get("total_count", 0),
                )
            except httpx.HTTPError as e:
                logger.warning("facebook.metrics.error", post_id=post_id, error=str(e))
        return PostMetrics()
