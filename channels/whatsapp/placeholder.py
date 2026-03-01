"""WhatsApp Business API adapter — placeholder for future implementation.

This module will implement the ChannelAdapter interface for WhatsApp
Business API when the platform expands to support WhatsApp as a
secondary channel.

See AGENTS.md §8.3 for planned implementation details.
"""

from __future__ import annotations

from channels.base import Button, ChannelAdapter, IncomingMessage


class WhatsAppAdapter(ChannelAdapter):
    """WhatsApp Business API adapter — stub implementation.

    Raises NotImplementedError for all methods. Will be implemented
    in a future phase when WhatsApp Business API integration is prioritized.
    """

    async def send_message(self, chat_id: str, text: str) -> None:
        """Send a text message via WhatsApp."""
        raise NotImplementedError("WhatsApp channel not yet implemented")

    async def send_rich_message(
        self, chat_id: str, text: str, buttons: list[list[Button]]
    ) -> None:
        """Send a message with interactive buttons via WhatsApp."""
        raise NotImplementedError("WhatsApp channel not yet implemented")

    async def process_incoming(self, payload: dict) -> IncomingMessage | None:
        """Process incoming WhatsApp webhook payload."""
        raise NotImplementedError("WhatsApp channel not yet implemented")

    async def setup_webhook(self, url: str) -> bool:
        """Register webhook with WhatsApp Business API."""
        raise NotImplementedError("WhatsApp channel not yet implemented")

    async def answer_callback(self, callback_id: str, text: str | None = None) -> None:
        """Acknowledge a callback (not applicable for WhatsApp)."""
        raise NotImplementedError("WhatsApp channel not yet implemented")
