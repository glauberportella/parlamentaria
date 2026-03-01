"""WhatsApp Business API adapter.

Implements the ChannelAdapter interface for WhatsApp Cloud API (Meta).
Uses httpx for async HTTP requests to the Graph API.

Key features:
- Send text messages and interactive button messages
- Process incoming webhook payloads (text and button replies)
- Webhook verification (challenge/response)
- Proper error handling and logging

Environment variables required:
- WHATSAPP_API_TOKEN: Permanent or temporary access token
- WHATSAPP_PHONE_NUMBER_ID: Phone number ID from Meta Business Suite
- WHATSAPP_WEBHOOK_VERIFY_TOKEN: Token for webhook verification
"""

from __future__ import annotations

import hmac
import hashlib
from typing import Any

import httpx

from app.config import settings
from app.logging import get_logger
from channels.base import Button, ChannelAdapter, IncomingMessage

logger = get_logger(__name__)


class WhatsAppAdapter(ChannelAdapter):
    """WhatsApp Business Cloud API adapter.

    Sends and receives messages via Meta's Graph API.
    """

    def __init__(self) -> None:
        self._base_url = (
            f"{settings.whatsapp_api_base_url}/{settings.whatsapp_phone_number_id}"
        )
        self._headers = {
            "Authorization": f"Bearer {settings.whatsapp_api_token}",
            "Content-Type": "application/json",
        }

    async def send_message(self, chat_id: str, text: str) -> None:
        """Send a plain text message to a WhatsApp user.

        Args:
            chat_id: Recipient's WhatsApp phone number (with country code).
            text: Message body text (max 4096 chars).
        """
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": chat_id,
            "type": "text",
            "text": {"preview_url": False, "body": text[:4096]},
        }
        await self._send_request(payload)

    async def send_rich_message(
        self, chat_id: str, text: str, buttons: list[list[Button]]
    ) -> None:
        """Send an interactive message with buttons via WhatsApp.

        WhatsApp interactive messages support up to 3 reply buttons.
        If more buttons are provided, extras are truncated.

        Args:
            chat_id: Recipient's WhatsApp phone number.
            text: Message body text.
            buttons: Rows of buttons (flattened; max 3 total).
        """
        # Flatten buttons and limit to WhatsApp's max of 3
        flat_buttons = [btn for row in buttons for btn in row][:3]

        wa_buttons = [
            {
                "type": "reply",
                "reply": {
                    "id": btn.callback_data[:256],
                    "title": btn.text[:20],  # WhatsApp max title: 20 chars
                },
            }
            for btn in flat_buttons
        ]

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": chat_id,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": text[:1024]},
                "action": {"buttons": wa_buttons},
            },
        }
        await self._send_request(payload)

    async def process_incoming(self, payload: dict) -> IncomingMessage | None:
        """Parse a WhatsApp Cloud API webhook payload.

        Extracts the first message from the webhook entry. Handles
        both regular text messages and interactive button replies.

        Args:
            payload: Raw JSON from the WhatsApp webhook.

        Returns:
            IncomingMessage or None if the payload is not a user message.
        """
        try:
            entry = payload.get("entry", [])
            if not entry:
                return None

            changes = entry[0].get("changes", [])
            if not changes:
                return None

            value = changes[0].get("value", {})
            messages = value.get("messages", [])
            if not messages:
                return None

            msg = messages[0]
            contact = value.get("contacts", [{}])[0]

            from_number = msg.get("from", "")
            msg_type = msg.get("type", "")

            text = ""
            callback_data = None

            if msg_type == "text":
                text = msg.get("text", {}).get("body", "")
            elif msg_type == "interactive":
                interactive = msg.get("interactive", {})
                interactive_type = interactive.get("type", "")
                if interactive_type == "button_reply":
                    reply = interactive.get("button_reply", {})
                    text = reply.get("title", "")
                    callback_data = reply.get("id", "")
                elif interactive_type == "list_reply":
                    reply = interactive.get("list_reply", {})
                    text = reply.get("title", "")
                    callback_data = reply.get("id", "")
            else:
                # Unsupported message type (image, audio, etc.)
                logger.info("whatsapp.unsupported_message_type", type=msg_type)
                return None

            if not text and not callback_data:
                return None

            return IncomingMessage(
                chat_id=from_number,
                user_id=from_number,
                text=text,
                username=contact.get("profile", {}).get("name"),
                first_name=contact.get("profile", {}).get("name"),
                callback_data=callback_data,
                channel="whatsapp",
                raw_payload=payload,
            )

        except (KeyError, IndexError) as e:
            logger.warning("whatsapp.parse_error", error=str(e))
            return None

    async def setup_webhook(self, url: str) -> bool:
        """Configure webhook with WhatsApp Business API.

        WhatsApp webhook setup is done via Meta Business Suite (UI) or
        the App Dashboard, not via API. This method just validates the
        configuration is present.

        Args:
            url: Webhook URL (for reference — actual setup is via Meta dashboard).

        Returns:
            True if WhatsApp API credentials are configured.
        """
        configured = bool(
            settings.whatsapp_api_token
            and settings.whatsapp_phone_number_id
        )
        if configured:
            logger.info("whatsapp.webhook.configured", url=url)
        else:
            logger.warning("whatsapp.webhook.not_configured")
        return configured

    async def answer_callback(self, callback_id: str, text: str | None = None) -> None:
        """Acknowledge a callback (WhatsApp marks messages as read).

        Unlike Telegram, WhatsApp doesn't have explicit callback answers.
        We mark the message as read instead.

        Args:
            callback_id: The message ID to mark as read.
            text: Ignored for WhatsApp.
        """
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": callback_id,
        }
        try:
            await self._send_request(payload, endpoint="/messages")
        except Exception:
            pass  # Best-effort — don't fail if read receipt fails

    # --- Internal helpers ---

    async def _send_request(
        self, payload: dict[str, Any], endpoint: str = "/messages"
    ) -> dict:
        """Send a request to the WhatsApp Cloud API.

        Args:
            payload: JSON body to send.
            endpoint: API endpoint path (default: /messages).

        Returns:
            Response JSON from the API.

        Raises:
            httpx.HTTPStatusError: If the API returns a non-2xx status.
        """
        url = f"{self._base_url}{endpoint}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload, headers=self._headers)
            resp.raise_for_status()
            result = resp.json()
            logger.debug(
                "whatsapp.api.response",
                status=resp.status_code,
                endpoint=endpoint,
            )
            return result


def verify_webhook_signature(
    payload_body: bytes, signature: str, app_secret: str
) -> bool:
    """Verify the webhook payload signature from Meta.

    Meta signs webhook payloads with HMAC-SHA256 using the app secret.
    The signature is sent in the X-Hub-Signature-256 header.

    Args:
        payload_body: Raw request body bytes.
        signature: Value of X-Hub-Signature-256 header.
        app_secret: Facebook app secret.

    Returns:
        True if signature is valid.
    """
    if not signature or not app_secret:
        return False
    expected = "sha256=" + hmac.new(
        app_secret.encode(), payload_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)


def verify_webhook_challenge(
    mode: str | None, token: str | None, challenge: str | None
) -> str | None:
    """Verify the webhook subscription challenge from Meta.

    Meta sends a GET request with hub.mode, hub.verify_token, and
    hub.challenge when subscribing a webhook. Return the challenge
    if verification passes.

    Args:
        mode: hub.mode parameter (should be "subscribe").
        token: hub.verify_token parameter.
        challenge: hub.challenge parameter.

    Returns:
        The challenge string if valid, None otherwise.
    """
    if mode == "subscribe" and token == settings.whatsapp_webhook_verify_token:
        logger.info("whatsapp.webhook.verified")
        return challenge
    logger.warning("whatsapp.webhook.verification_failed")
    return None
