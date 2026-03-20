"""LinkedIn publisher using httpx (Marketing API)."""

import httpx

from app.config import settings
from app.integrations.social_publisher import PostMetrics, PublishResult, SocialPublisher
from app.logging import get_logger

logger = get_logger(__name__)

LINKEDIN_API_BASE = "https://api.linkedin.com"


class LinkedInPublisher(SocialPublisher):
    """Publishes posts to a LinkedIn Organization Page."""

    def __init__(self) -> None:
        self._org_id = settings.linkedin_organization_id
        self._token = settings.linkedin_access_token
        self._headers = {
            "Authorization": f"Bearer {self._token}",
            "LinkedIn-Version": "202401",
            "X-Restli-Protocol-Version": "2.0.0",
        }

    async def publish_text(self, text: str) -> PublishResult:
        """Publish a text-only post to LinkedIn."""
        url = f"{LINKEDIN_API_BASE}/rest/posts"
        payload = {
            "author": f"urn:li:organization:{self._org_id}",
            "commentary": text,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.post(
                    url,
                    json=payload,
                    headers={**self._headers, "Content-Type": "application/json"},
                )
                resp.raise_for_status()
                post_id = resp.headers.get("x-restli-id", "")
                return PublishResult(
                    success=True,
                    post_id=post_id,
                    url=f"https://linkedin.com/feed/update/{post_id}",
                )
            except httpx.HTTPError as e:
                logger.error("linkedin.publish_text.error", error=str(e))
                return PublishResult(
                    success=False,
                    error="Falha ao publicar no LinkedIn.",
                )

    async def publish_with_image(self, text: str, image_path: str) -> PublishResult:
        """Publish a post with image to LinkedIn (upload + post)."""
        async with httpx.AsyncClient(timeout=60) as client:
            try:
                # Step 1: Initialize image upload
                init_url = f"{LINKEDIN_API_BASE}/rest/images?action=initializeUpload"
                init_payload = {
                    "initializeUploadRequest": {
                        "owner": f"urn:li:organization:{self._org_id}",
                    }
                }
                init_resp = await client.post(
                    init_url,
                    json=init_payload,
                    headers={**self._headers, "Content-Type": "application/json"},
                )
                init_resp.raise_for_status()
                init_data = init_resp.json()["value"]
                upload_url = init_data["uploadUrl"]
                image_urn = init_data["image"]

                # Step 2: Upload image bytes
                with open(image_path, "rb") as f:
                    upload_resp = await client.put(
                        upload_url,
                        content=f.read(),
                        headers={
                            "Authorization": f"Bearer {self._token}",
                            "Content-Type": "image/png",
                        },
                    )
                    upload_resp.raise_for_status()

                # Step 3: Create post with image reference
                post_url = f"{LINKEDIN_API_BASE}/rest/posts"
                post_payload = {
                    "author": f"urn:li:organization:{self._org_id}",
                    "commentary": text,
                    "visibility": "PUBLIC",
                    "distribution": {
                        "feedDistribution": "MAIN_FEED",
                        "targetEntities": [],
                        "thirdPartyDistributionChannels": [],
                    },
                    "content": {
                        "media": {"id": image_urn},
                    },
                    "lifecycleState": "PUBLISHED",
                }
                post_resp = await client.post(
                    post_url,
                    json=post_payload,
                    headers={**self._headers, "Content-Type": "application/json"},
                )
                post_resp.raise_for_status()
                post_id = post_resp.headers.get("x-restli-id", "")

                return PublishResult(
                    success=True,
                    post_id=post_id,
                    url=f"https://linkedin.com/feed/update/{post_id}",
                )
            except (httpx.HTTPError, OSError, KeyError) as e:
                logger.error("linkedin.publish_with_image.error", error=str(e))
                return PublishResult(
                    success=False,
                    error="Falha ao publicar no LinkedIn.",
                )

    async def delete_post(self, post_id: str) -> bool:
        """Delete a LinkedIn post."""
        url = f"{LINKEDIN_API_BASE}/rest/posts/{post_id}"
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                resp = await client.delete(url, headers=self._headers)
                resp.raise_for_status()
                return True
            except httpx.HTTPError as e:
                logger.error("linkedin.delete.error", post_id=post_id, error=str(e))
                return False

    async def get_metrics(self, post_id: str) -> PostMetrics:
        """Fetch LinkedIn post metrics (limited in free tier)."""
        # LinkedIn metrics require Marketing Developer Platform access
        logger.info("linkedin.metrics.not_implemented", post_id=post_id)
        return PostMetrics()
