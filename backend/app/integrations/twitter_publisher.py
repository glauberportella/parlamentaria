"""Twitter/X publisher using tweepy (API v2 + v1.1 media upload)."""

import asyncio
from functools import partial

import tweepy

from app.config import settings
from app.integrations.social_publisher import PostMetrics, PublishResult, SocialPublisher
from app.logging import get_logger

logger = get_logger(__name__)


class TwitterPublisher(SocialPublisher):
    """Publishes posts to Twitter/X via API v2."""

    def __init__(self) -> None:
        self._client = tweepy.Client(
            consumer_key=settings.twitter_api_key,
            consumer_secret=settings.twitter_api_secret,
            access_token=settings.twitter_access_token,
            access_token_secret=settings.twitter_access_token_secret,
            wait_on_rate_limit=True,
        )
        # v1.1 API for media upload (not available in v2)
        auth = tweepy.OAuth1UserHandler(
            settings.twitter_api_key,
            settings.twitter_api_secret,
            settings.twitter_access_token,
            settings.twitter_access_token_secret,
        )
        self._api_v1 = tweepy.API(auth)

    def _create_tweet(self, text: str, media_ids: list[int] | None = None) -> dict:
        """Synchronous tweet creation."""
        kwargs: dict = {"text": text}
        if media_ids:
            kwargs["media_ids"] = media_ids
        response = self._client.create_tweet(**kwargs)
        return {"id": str(response.data["id"])}

    def _upload_media(self, image_path: str) -> int:
        """Synchronous media upload via v1.1 API."""
        media = self._api_v1.media_upload(filename=image_path)
        return media.media_id

    async def publish_text(self, text: str) -> PublishResult:
        """Publish a text-only tweet."""
        try:
            data = await asyncio.to_thread(self._create_tweet, text)
            tweet_id = data["id"]
            return PublishResult(
                success=True,
                post_id=tweet_id,
                url=f"https://x.com/i/status/{tweet_id}",
            )
        except tweepy.TweepyException as e:
            logger.error("twitter.publish_text.error", error=str(e))
            return PublishResult(success=False, error="Falha ao publicar no Twitter.")

    async def publish_with_image(self, text: str, image_path: str) -> PublishResult:
        """Publish a tweet with image."""
        try:
            media_id = await asyncio.to_thread(self._upload_media, image_path)
            data = await asyncio.to_thread(self._create_tweet, text, [media_id])
            tweet_id = data["id"]
            return PublishResult(
                success=True,
                post_id=tweet_id,
                url=f"https://x.com/i/status/{tweet_id}",
            )
        except tweepy.TweepyException as e:
            logger.error("twitter.publish_with_image.error", error=str(e))
            return PublishResult(success=False, error="Falha ao publicar no Twitter.")

    async def delete_post(self, post_id: str) -> bool:
        """Delete a tweet."""
        try:
            await asyncio.to_thread(self._client.delete_tweet, id=post_id)
            return True
        except tweepy.TweepyException as e:
            logger.error("twitter.delete.error", post_id=post_id, error=str(e))
            return False

    async def get_metrics(self, post_id: str) -> PostMetrics:
        """Fetch tweet metrics."""
        try:
            response = await asyncio.to_thread(
                partial(
                    self._client.get_tweet,
                    id=post_id,
                    tweet_fields=["public_metrics"],
                )
            )
            if response.data and response.data.public_metrics:
                m = response.data.public_metrics
                return PostMetrics(
                    likes=m.get("like_count", 0),
                    shares=m.get("retweet_count", 0),
                    comments=m.get("reply_count", 0),
                    impressions=m.get("impression_count", 0),
                )
        except tweepy.TweepyException as e:
            logger.warning("twitter.metrics.error", post_id=post_id, error=str(e))
        return PostMetrics()
