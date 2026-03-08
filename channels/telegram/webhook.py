"""FastAPI webhook endpoint for Telegram Bot API.

This module provides the webhook integration that receives Telegram updates,
processes them through the channel adapter + ADK agent, and sends responses
back to the user.
"""

from __future__ import annotations

import hmac
import hashlib

from fastapi import APIRouter, Header, HTTPException, Request

from app.config import settings
from app.logging import get_logger
from app.middleware import limiter
from channels.telegram.bot import TelegramAdapter
from channels.telegram.enhancer import enhance_response
from channels.telegram.formatter import format_agent_response
from channels.telegram.handlers import handle_callback, handle_command

logger = get_logger(__name__)

router = APIRouter(tags=["telegram"])

# Module-level adapter instance (lazy-initialized)
_adapter: TelegramAdapter | None = None


def get_adapter() -> TelegramAdapter:
    """Get or create the Telegram adapter singleton."""
    global _adapter
    if _adapter is None:
        _adapter = TelegramAdapter()
    return _adapter


def _validate_secret_token(
    token: str | None, expected: str | None
) -> bool:
    """Validate the Telegram webhook secret token.

    Args:
        token: Token from X-Telegram-Bot-Api-Secret-Token header.
        expected: Expected secret from settings.

    Returns:
        True if valid (or no secret configured).
    """
    if not expected:
        return True  # No secret configured — skip validation
    if not token:
        return False
    return hmac.compare_digest(token, expected)


@router.post("/webhook/telegram")
@limiter.limit("60/minute")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(None),
) -> dict:
    """Receive and process Telegram Bot API webhook updates.

    Flow:
    1. Validate webhook secret token
    2. Parse incoming update via TelegramAdapter
    3. Handle commands or route to ADK agent
    4. Send response back to user

    Args:
        request: FastAPI request with JSON body.
        x_telegram_bot_api_secret_token: Secret token from Telegram.

    Returns:
        Status dict acknowledging the update.
    """
    # Validate secret token
    if not _validate_secret_token(
        x_telegram_bot_api_secret_token,
        settings.telegram_webhook_secret,
    ):
        logger.warning("telegram.webhook.invalid_secret")
        raise HTTPException(status_code=403, detail="Invalid secret token")

    # Parse payload
    try:
        payload = await request.json()
    except Exception:
        logger.warning("telegram.webhook.invalid_json")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    adapter = get_adapter()

    # Parse into normalized message
    message = await adapter.process_incoming(payload)
    if message is None:
        return {"status": "ignored"}

    logger.info(
        "telegram.webhook.received",
        chat_id=message.chat_id,
        user_id=message.user_id,
        has_callback=message.callback_data is not None,
        text_preview=message.text[:50] if message.text else "",
    )

    try:
        # Handle callback queries (button presses)
        if message.callback_data:
            result = await handle_callback(message)

            # Answer the callback query (removes loading spinner)
            callback_query_id = payload.get("callback_query", {}).get("id")
            if callback_query_id and result.get("callback_answer"):
                await adapter.answer_callback(callback_query_id, result["callback_answer"])

            # Send direct text response if provided
            if result.get("text"):
                if result.get("buttons"):
                    await adapter.send_rich_message(
                        message.chat_id, result["text"], result["buttons"]
                    )
                else:
                    await adapter.send_message(message.chat_id, result["text"])

            # Forward to agent if needed
            if result.get("to_agent"):
                await adapter.send_chat_action(message.chat_id)
                agent_response = await _run_agent(message.chat_id, message.user_id, result["to_agent"])
                formatted = format_agent_response(agent_response)
                enhanced_text, buttons = enhance_response(formatted, result["to_agent"])
                if buttons:
                    await adapter.send_rich_message(message.chat_id, enhanced_text, buttons)
                else:
                    await adapter.send_message(message.chat_id, enhanced_text)

            return {"status": "processed"}

        # Handle commands
        if message.text.startswith("/"):
            result = await handle_command(message)

            # Check if /reset needs session reset
            if result.get("reset_session"):
                from agents.parlamentar.runner import reset_session
                await reset_session(
                    user_id=message.user_id,
                    session_id=message.chat_id,
                )

            if result.get("handled"):
                if result.get("buttons"):
                    await adapter.send_rich_message(
                        message.chat_id, result["text"], result["buttons"]
                    )
                else:
                    await adapter.send_message(message.chat_id, result["text"])
                return {"status": "processed"}

            # Not a built-in command — forward full text to agent
            # (e.g., /proposicoes, /votar become agent queries)
            agent_text = message.text
        else:
            # Regular free-text message
            agent_text = message.text

        # Route to ADK agent
        await adapter.send_chat_action(message.chat_id)
        agent_response = await _run_agent(message.chat_id, message.user_id, agent_text)
        formatted = format_agent_response(agent_response)
        enhanced_text, buttons = enhance_response(formatted, agent_text)
        if buttons:
            await adapter.send_rich_message(message.chat_id, enhanced_text, buttons)
        else:
            await adapter.send_message(message.chat_id, enhanced_text)

    except Exception as e:
        logger.error(
            "telegram.webhook.processing_error",
            chat_id=message.chat_id,
            error=str(e),
        )
        try:
            await adapter.send_message(
                message.chat_id,
                "😔 Desculpe, ocorreu um erro ao processar sua mensagem. "
                "Tente novamente em alguns instantes.",
            )
        except Exception:
            pass  # Best-effort error message

    return {"status": "processed"}


async def _run_agent(chat_id: str, user_id: str, text: str) -> str:
    """Run the ADK agent and return the response text.

    Args:
        chat_id: Telegram chat ID (used as session_id).
        user_id: Telegram user ID.
        text: User message text.

    Returns:
        Agent response text.
    """
    from agents.parlamentar.runner import run_agent

    return await run_agent(
        user_id=user_id,
        session_id=chat_id,
        message=text,
    )
