"""Reddit publisher using PRAW (r/parlamentaria only)."""

import asyncio
import json
from functools import partial

from app.config import settings
from app.integrations.social_publisher import (
    PostMetrics,
    PublishResult,
    SocialPublisher,
)
from app.logging import get_logger

logger = get_logger(__name__)


class RedditPublisher(SocialPublisher):
    """Publishes posts to Reddit via PRAW (sync wrapped with asyncio.to_thread)."""

    def _get_reddit(self):
        """Create a PRAW Reddit instance (lazily, per-call)."""
        import praw

        return praw.Reddit(
            client_id=settings.reddit_client_id,
            client_secret=settings.reddit_client_secret,
            username=settings.reddit_username,
            password=settings.reddit_password,
            user_agent="parlamentaria:v1.0 (by /u/parlamentaria)",
        )

    async def publish_text(self, text: str) -> PublishResult:
        """Submit a text post to the configured subreddit."""
        lines = text.strip().split("\n", 1)
        title = lines[0][:300]
        body = lines[1] if len(lines) > 1 else ""

        try:
            submission = await asyncio.to_thread(
                partial(self._submit_text, title, body)
            )
            return PublishResult(
                success=True,
                post_id=submission.id,
                url=f"https://reddit.com{submission.permalink}",
            )
        except Exception as e:
            logger.error("reddit.publish_text.error", error=str(e))
            return PublishResult(success=False, error="Falha ao publicar no Reddit.")

    def _submit_text(self, title: str, body: str):
        """Synchronous text post submission."""
        reddit = self._get_reddit()
        subreddit = reddit.subreddit(settings.reddit_subreddit)
        return subreddit.submit(title=title, selftext=body)

    async def publish_with_image(self, text: str, image_path: str) -> PublishResult:
        """Submit an image post to the configured subreddit."""
        lines = text.strip().split("\n", 1)
        title = lines[0][:300]

        try:
            submission = await asyncio.to_thread(
                partial(self._submit_image, title, image_path)
            )
            return PublishResult(
                success=True,
                post_id=submission.id,
                url=f"https://reddit.com{submission.permalink}",
            )
        except Exception as e:
            logger.error("reddit.publish_with_image.error", error=str(e))
            return PublishResult(success=False, error="Falha ao publicar no Reddit.")

    def _submit_image(self, title: str, image_path: str):
        """Synchronous image post submission."""
        reddit = self._get_reddit()
        subreddit = reddit.subreddit(settings.reddit_subreddit)
        return subreddit.submit_image(title=title, image_path=image_path)

    async def delete_post(self, post_id: str) -> bool:
        """Delete a Reddit submission."""
        try:
            await asyncio.to_thread(partial(self._delete, post_id))
            return True
        except Exception as e:
            logger.error("reddit.delete.error", post_id=post_id, error=str(e))
            return False

    def _delete(self, post_id: str) -> None:
        """Synchronous deletion."""
        reddit = self._get_reddit()
        submission = reddit.submission(id=post_id)
        submission.delete()

    async def get_metrics(self, post_id: str) -> PostMetrics:
        """Fetch metrics for a Reddit submission."""
        try:
            data = await asyncio.to_thread(partial(self._fetch_metrics, post_id))
            return data
        except Exception as e:
            logger.error("reddit.get_metrics.error", post_id=post_id, error=str(e))
            return PostMetrics()

    def _fetch_metrics(self, post_id: str) -> PostMetrics:
        """Synchronous metrics fetch."""
        reddit = self._get_reddit()
        submission = reddit.submission(id=post_id)
        submission._fetch()
        return PostMetrics(
            likes=submission.score,
            comments=submission.num_comments,
            impressions=getattr(submission, "view_count", None),
        )
