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

        # Check rate limit for free-tier users before calling the agent
        rate_result = await _check_rate_limit(message.chat_id)
        if not rate_result["allowed"]:
            rate_msg = _format_rate_limit_msg(rate_result)
            premium_buttons = _get_premium_upgrade_buttons()
            if premium_buttons:
                await adapter.send_rich_message(message.chat_id, rate_msg, premium_buttons)
            else:
                await adapter.send_message(message.chat_id, rate_msg)
            return {"status": "rate_limited"}

        # Route to ADK agent
        await adapter.send_chat_action(message.chat_id)
        agent_response = await _run_agent(message.chat_id, message.user_id, agent_text)
        formatted = format_agent_response(agent_response)
        enhanced_text, buttons = enhance_response(formatted, agent_text)
        if buttons:
            await adapter.send_rich_message(message.chat_id, enhanced_text, buttons)
        else:
            await adapter.send_message(message.chat_id, enhanced_text)

        # Increment counter after successful agent response
        await _increment_rate_counter(message.chat_id)

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


async def _check_rate_limit(chat_id: str) -> dict:
    """Check rate limit via premium plugin (fail-open if not installed)."""
    try:
        from premium.billing.rate_limiter import check_chat_rate_limit

        # Get eleitor plan from DB
        plano = await _get_eleitor_plano(chat_id)
        return await check_chat_rate_limit(chat_id, plano)
    except ImportError:
        return {"allowed": True, "remaining": None, "limit": None, "reset_at": None}
    except Exception:
        logger.debug("rate_limit.check_failed", exc_info=True)
        return {"allowed": True, "remaining": None, "limit": None, "reset_at": None}


async def _increment_rate_counter(chat_id: str) -> None:
    """Increment rate limit counter via premium plugin."""
    try:
        from premium.billing.rate_limiter import increment_chat_counter

        plano = await _get_eleitor_plano(chat_id)
        await increment_chat_counter(chat_id, plano)
    except ImportError:
        pass
    except Exception:
        logger.debug("rate_limit.increment_failed", exc_info=True)


async def _get_eleitor_plano(chat_id: str) -> str:
    """Get the eleitor's plan from DB. Returns 'GRATUITO' if not found."""
    try:
        from app.db.session import async_session_factory
        from sqlalchemy import select
        from app.domain.eleitor import Eleitor

        async with async_session_factory() as session:
            result = await session.execute(
                select(Eleitor.plano).where(Eleitor.chat_id == str(chat_id))
            )
            plano = result.scalar_one_or_none()
            return plano or "GRATUITO"
    except Exception:
        return "GRATUITO"


def _format_rate_limit_msg(rate_result: dict) -> str:
    """Format rate limit message for the user."""
    try:
        from premium.billing.rate_limiter import format_rate_limit_message
        return format_rate_limit_message(
            rate_result.get("remaining"), rate_result.get("limit"), rate_result.get("reset_at")
        )
    except ImportError:
        return "⚠️ Limite diário atingido. Tente novamente amanhã."


def _get_premium_upgrade_buttons() -> list | None:
    """Get upgrade buttons if premium is available."""
    try:
        from channels.base import Button
        return [
            [
                Button(text="⭐ Conhecer Premium", callback_data="menu:premium"),
                Button(text="📋 Menu", callback_data="menu:main"),
            ]
        ]
    except Exception:
        return None
