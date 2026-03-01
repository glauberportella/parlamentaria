"""Abstract base class for messaging channel adapters.

All channel adapters (Telegram, WhatsApp, etc.) must implement this interface.
This ensures the agent layer remains channel-agnostic — the core logic works
independently of the underlying messaging platform.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class IncomingMessage:
    """Normalized representation of an incoming user message.

    Attributes:
        chat_id: Unique identifier of the chat/conversation.
        user_id: Unique identifier of the user/sender.
        text: The message text content.
        username: Optional username of the sender.
        first_name: Optional first name of the sender.
        callback_data: Optional callback data from inline keyboard button press.
        channel: Channel identifier (e.g., 'telegram', 'whatsapp').
        raw_payload: Original raw payload from the channel (for debugging).
    """

    chat_id: str
    user_id: str
    text: str
    username: str | None = None
    first_name: str | None = None
    callback_data: str | None = None
    channel: str = "unknown"
    raw_payload: dict | None = None


@dataclass
class Button:
    """A button for rich messages (inline keyboard).

    Attributes:
        text: Display text of the button.
        callback_data: Data sent back when button is pressed.
    """

    text: str
    callback_data: str


class ChannelAdapter(ABC):
    """Abstract base class for messaging channel adapters.

    Each adapter handles the specifics of a messaging platform
    while exposing a uniform interface to the agent layer.
    """

    @abstractmethod
    async def send_message(self, chat_id: str, text: str) -> None:
        """Send a plain text message to the user.

        Args:
            chat_id: Target chat/conversation identifier.
            text: Message text to send.
        """
        ...

    @abstractmethod
    async def send_rich_message(
        self, chat_id: str, text: str, buttons: list[list[Button]]
    ) -> None:
        """Send a message with inline keyboard buttons.

        Args:
            chat_id: Target chat/conversation identifier.
            text: Message text to send.
            buttons: Rows of buttons (list of rows, each row is a list of Buttons).
        """
        ...

    @abstractmethod
    async def process_incoming(self, payload: dict) -> IncomingMessage | None:
        """Parse a raw webhook payload into an IncomingMessage.

        Args:
            payload: Raw JSON payload from the messaging platform webhook.

        Returns:
            Normalized IncomingMessage, or None if the payload should be ignored
            (e.g., non-text updates, edits, etc.).
        """
        ...

    @abstractmethod
    async def setup_webhook(self, url: str) -> bool:
        """Configure the webhook URL with the messaging platform.

        Args:
            url: Public HTTPS URL to receive webhook callbacks.

        Returns:
            True if webhook was set up successfully.
        """
        ...

    @abstractmethod
    async def answer_callback(self, callback_id: str, text: str | None = None) -> None:
        """Acknowledge a callback query (button press).

        Args:
            callback_id: The callback query ID to acknowledge.
            text: Optional toast notification text.
        """
        ...
