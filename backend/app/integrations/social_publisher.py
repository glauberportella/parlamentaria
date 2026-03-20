"""Abstract base class for social media publishers + Factory."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.config import settings
from app.domain.social_post import RedeSocial
from app.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PublishResult:
    """Result of a publish operation."""

    success: bool
    post_id: str | None = None
    url: str | None = None
    error: str | None = None


@dataclass
class PostMetrics:
    """Metrics for a published post."""

    likes: int = 0
    shares: int = 0
    comments: int = 0
    impressions: int = 0


class SocialPublisher(ABC):
    """Interface for publishing to a social network."""

    @abstractmethod
    async def publish_text(self, text: str) -> PublishResult:
        """Publish a text-only post."""
        ...

    @abstractmethod
    async def publish_with_image(self, text: str, image_path: str) -> PublishResult:
        """Publish a post with text and image."""
        ...

    @abstractmethod
    async def delete_post(self, post_id: str) -> bool:
        """Delete a published post."""
        ...

    @abstractmethod
    async def get_metrics(self, post_id: str) -> PostMetrics:
        """Fetch metrics for a published post."""
        ...


@dataclass
class DiscordEmbed:
    """Discord rich embed structure."""

    title: str = ""
    description: str = ""
    color: int = 0x60A5FA
    fields: list[dict] = field(default_factory=list)
    image_url: str | None = None
    footer_text: str = "parlamentaria.app — democracia participativa"
    timestamp: str | None = None


def get_publisher(rede: RedeSocial) -> SocialPublisher:
    """Factory: instantiate the correct publisher for a given social network.

    Args:
        rede: Target social network.

    Returns:
        Configured publisher instance.

    Raises:
        ValueError: If network is not supported or not enabled.
    """
    enabled_networks = {n.strip() for n in settings.social_networks.split(",")}
    if rede.value not in enabled_networks:
        raise ValueError(f"Rede social '{rede.value}' não está habilitada.")

    if rede == RedeSocial.TWITTER:
        if not settings.twitter_enabled:
            raise ValueError("Twitter está desabilitado (TWITTER_ENABLED=false).")
        from app.integrations.twitter_publisher import TwitterPublisher

        return TwitterPublisher()

    if rede == RedeSocial.FACEBOOK:
        if not settings.facebook_enabled:
            raise ValueError("Facebook está desabilitado (FACEBOOK_ENABLED=false).")
        from app.integrations.facebook_publisher import FacebookPublisher

        return FacebookPublisher()

    if rede == RedeSocial.INSTAGRAM:
        if not settings.instagram_enabled:
            raise ValueError("Instagram está desabilitado (INSTAGRAM_ENABLED=false).")
        from app.integrations.instagram_publisher import InstagramPublisher

        return InstagramPublisher()

    if rede == RedeSocial.LINKEDIN:
        if not settings.linkedin_enabled:
            raise ValueError("LinkedIn está desabilitado (LINKEDIN_ENABLED=false).")
        from app.integrations.linkedin_publisher import LinkedInPublisher

        return LinkedInPublisher()

    if rede == RedeSocial.DISCORD:
        if not settings.discord_enabled:
            raise ValueError("Discord está desabilitado (DISCORD_ENABLED=false).")
        from app.integrations.discord_publisher import DiscordPublisher

        return DiscordPublisher()

    if rede == RedeSocial.REDDIT:
        if not settings.reddit_enabled:
            raise ValueError("Reddit está desabilitado (REDDIT_ENABLED=false).")
        from app.integrations.reddit_publisher import RedditPublisher

        return RedditPublisher()

    raise ValueError(f"Rede social não suportada: {rede.value}")


def get_active_networks() -> list[RedeSocial]:
    """Return list of currently enabled social networks."""
    enabled_csv = {n.strip() for n in settings.social_networks.split(",")}
    active: list[RedeSocial] = []

    network_checks = {
        RedeSocial.TWITTER: settings.twitter_enabled,
        RedeSocial.FACEBOOK: settings.facebook_enabled,
        RedeSocial.INSTAGRAM: settings.instagram_enabled,
        RedeSocial.LINKEDIN: settings.linkedin_enabled,
        RedeSocial.DISCORD: settings.discord_enabled,
        RedeSocial.REDDIT: settings.reddit_enabled,
    }

    for rede, is_enabled in network_checks.items():
        if rede.value in enabled_csv and is_enabled:
            active.append(rede)

    return active
