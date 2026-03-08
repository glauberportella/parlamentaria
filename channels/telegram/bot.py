"""Telegram Bot adapter — implements ChannelAdapter for Telegram Bot API.

Uses python-telegram-bot for rich Telegram interactions (inline keyboards,
callback queries, etc.) and bridges messages to/from the ADK Runner.
"""

from __future__ import annotations

import re as _re

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode

from app.config import settings
from app.logging import get_logger
from channels.base import Button, ChannelAdapter, IncomingMessage
from channels.telegram.formatter import split_message

logger = get_logger(__name__)


class TelegramAdapter(ChannelAdapter):
    """Telegram Bot API adapter.

    Wraps python-telegram-bot's Bot class to provide a channel-agnostic
    interface for sending/receiving messages via Telegram.
    """

    def __init__(self, token: str | None = None) -> None:
        """Initialize the Telegram adapter.

        Args:
            token: Bot API token. Defaults to settings.telegram_bot_token.
        """
        self._token = token or settings.telegram_bot_token
        self._bot = Bot(token=self._token)

    @property
    def bot(self) -> Bot:
        """Access the underlying python-telegram-bot Bot instance."""
        return self._bot

    async def send_message(self, chat_id: str, text: str) -> None:
        """Send a text message via Telegram.

        Splits long messages into chunks that fit Telegram's 4096-char
        limit and uses HTML parse mode.  If HTML parsing fails, falls
        back to plain text (HTML tags stripped).

        Args:
            chat_id: Telegram chat ID.
            text: Message text (Telegram HTML).
        """
        chunks = split_message(text)
        for chunk in chunks:
            await self._send_html_with_fallback(int(chat_id), chunk)

    async def _send_html_with_fallback(
        self, chat_id: int, text: str, **kwargs: object
    ) -> None:
        """Send a single message with HTML parse mode and plain-text fallback.

        If Telegram rejects the HTML (malformed tags), the message is
        resent with all HTML tags stripped so the user still gets a reply.

        Args:
            chat_id: Telegram numeric chat ID.
            text: Message text (Telegram HTML).
            **kwargs: Extra keyword arguments forwarded to ``send_message``.
        """
        try:
            await self._bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=ParseMode.HTML,
                **kwargs,
            )
        except Exception as e:
            error_msg = str(e).lower()
            if "can't parse entities" in error_msg or "can&#39;t parse" in error_msg:
                logger.warning(
                    "telegram.send_message.html_fallback",
                    chat_id=chat_id,
                    error=str(e),
                )
                plain = _re.sub(r"<[^>]+>", "", text)
                try:
                    await self._bot.send_message(
                        chat_id=chat_id, text=plain, **kwargs
                    )
                except Exception as inner:
                    logger.error(
                        "telegram.send_message.fallback_error",
                        chat_id=chat_id,
                        error=str(inner),
                    )
                    raise
            else:
                logger.error(
                    "telegram.send_message.error",
                    chat_id=chat_id,
                    error=str(e),
                )
                raise

    async def send_rich_message(
        self, chat_id: str, text: str, buttons: list[list[Button]]
    ) -> None:
        """Send a message with inline keyboard buttons.

        Args:
            chat_id: Telegram chat ID.
            text: Message text (Telegram HTML).
            buttons: Rows of Button objects to display as inline keyboard.
        """
        keyboard = [
            [
                InlineKeyboardButton(text=btn.text, callback_data=btn.callback_data)
                for btn in row
            ]
            for row in buttons
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            await self._bot.send_message(
                chat_id=int(chat_id),
                text=text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML,
            )
        except Exception as e:
            error_msg = str(e).lower()
            if "can't parse entities" in error_msg or "can&#39;t parse" in error_msg:
                logger.warning(
                    "telegram.send_rich_message.html_fallback",
                    chat_id=chat_id,
                    error=str(e),
                )
                plain = _re.sub(r"<[^>]+>", "", text)
                await self._bot.send_message(
                    chat_id=int(chat_id),
                    text=plain,
                    reply_markup=reply_markup,
                )
            else:
                logger.error(
                    "telegram.send_rich_message.error",
                    chat_id=chat_id,
                    error=str(e),
                )
                raise

    async def process_incoming(self, payload: dict) -> IncomingMessage | None:
        """Parse a raw Telegram webhook payload into an IncomingMessage.

        Handles both regular text messages and callback queries (button presses).

        Args:
            payload: Raw JSON from Telegram webhook.

        Returns:
            IncomingMessage or None if the update should be ignored.
        """
        try:
            update = Update.de_json(data=payload, bot=self._bot)
        except Exception as e:
            logger.warning("telegram.parse.error", error=str(e))
            return None

        # Handle callback queries (inline keyboard button presses)
        if update.callback_query:
            query = update.callback_query
            user = query.from_user
            chat_id = str(query.message.chat_id) if query.message else str(user.id)
            return IncomingMessage(
                chat_id=chat_id,
                user_id=str(user.id),
                text=query.data or "",
                username=user.username,
                first_name=user.first_name,
                callback_data=query.data,
                channel="telegram",
                raw_payload=payload,
            )

        # Handle regular text messages
        if update.message and update.message.text:
            msg = update.message
            user = msg.from_user
            return IncomingMessage(
                chat_id=str(msg.chat_id),
                user_id=str(user.id) if user else str(msg.chat_id),
                text=msg.text,
                username=user.username if user else None,
                first_name=user.first_name if user else None,
                channel="telegram",
                raw_payload=payload,
            )

        # Ignore non-text updates (photos, stickers, edits, etc.)
        logger.debug("telegram.update.ignored", update_id=update.update_id)
        return None

    async def setup_webhook(self, url: str) -> bool:
        """Register a webhook URL with Telegram Bot API.

        Args:
            url: Public HTTPS URL for receiving updates.

        Returns:
            True if webhook was set successfully.
        """
        try:
            secret_token = settings.telegram_webhook_secret or None
            result = await self._bot.set_webhook(
                url=url,
                secret_token=secret_token,
                allowed_updates=["message", "callback_query"],
            )
            logger.info("telegram.webhook.set", url=url, success=result)
            return result
        except Exception as e:
            logger.error("telegram.webhook.error", url=url, error=str(e))
            return False

    async def answer_callback(self, callback_id: str, text: str | None = None) -> None:
        """Acknowledge a callback query (button press).

        Args:
            callback_id: Telegram callback query ID.
            text: Optional notification text shown to the user.
        """
        try:
            await self._bot.answer_callback_query(
                callback_query_id=callback_id,
                text=text,
            )
        except Exception as e:
            logger.warning(
                "telegram.answer_callback.error",
                callback_id=callback_id,
                error=str(e),
            )
