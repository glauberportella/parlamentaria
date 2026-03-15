"""Twitter/X publisher using tweepy (API v2 + v1.1 media upload)."""

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

    async def publish_text(self, text: str) -> PublishResult:
        """Publish a text-only tweet."""
        try:
            response = self._client.create_tweet(text=text)
            tweet_id = str(response.data["id"])
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
            media = self._api_v1.media_upload(filename=image_path)
            response = self._client.create_tweet(
                text=text, media_ids=[media.media_id]
            )
            tweet_id = str(response.data["id"])
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
            self._client.delete_tweet(id=post_id)
            return True
        except tweepy.TweepyException as e:
            logger.error("twitter.delete.error", post_id=post_id, error=str(e))
            return False

    async def get_metrics(self, post_id: str) -> PostMetrics:
        """Fetch tweet metrics."""
        try:
            response = self._client.get_tweet(
                id=post_id,
                tweet_fields=["public_metrics"],
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
