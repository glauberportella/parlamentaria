"""Webhook endpoints for messaging channels (Telegram, WhatsApp).

Telegram webhook processing is delegated to the channel adapter module.
WhatsApp webhooks handle both verification (GET) and message (POST) flows.
"""

from fastapi import APIRouter, Query, Request
from fastapi.responses import PlainTextResponse, JSONResponse

from app.logging import get_logger
from app.middleware import limiter
from channels.telegram.webhook import router as telegram_router
from channels.whatsapp.adapter import (
    WhatsAppAdapter,
    verify_webhook_challenge,
)

router = APIRouter(tags=["webhooks"])
logger = get_logger(__name__)

# Include the Telegram webhook router (handles /webhook/telegram)
router.include_router(telegram_router)

# Singleton WhatsApp adapter
_whatsapp_adapter = WhatsAppAdapter()


@router.get("/webhook/whatsapp")
async def whatsapp_webhook_verify(
    request: Request,
    hub_mode: str | None = Query(None, alias="hub.mode"),
    hub_verify_token: str | None = Query(None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(None, alias="hub.challenge"),
) -> PlainTextResponse:
    """Handle WhatsApp webhook verification (Meta challenge/response).

    Meta sends a GET with hub.mode, hub.verify_token, hub.challenge.
    Return the challenge string as plain text if the token matches.
    """
    challenge = verify_webhook_challenge(hub_mode, hub_verify_token, hub_challenge)
    if challenge:
        return PlainTextResponse(content=challenge, status_code=200)
    return PlainTextResponse(content="Forbidden", status_code=403)


@router.post("/webhook/whatsapp")
@limiter.limit("60/minute")
async def whatsapp_webhook(request: Request) -> JSONResponse:
    """Receive WhatsApp Business API webhook events.

    Parses the incoming payload via the WhatsApp adapter,
    routes the message to the AI agent, and sends back the response.
    """
    payload = await request.json()

    incoming = await _whatsapp_adapter.process_incoming(payload)
    if not incoming:
        return JSONResponse({"status": "ignored"})

    try:
        # Check rate limit for free-tier users
        rate_result = await _wa_check_rate_limit(incoming.chat_id)
        if not rate_result["allowed"]:
            rate_msg = _wa_format_rate_limit_msg(rate_result)
            await _whatsapp_adapter.send_message(incoming.chat_id, rate_msg)
            return JSONResponse({"status": "rate_limited"})

        from agents.parlamentar.runner import run_agent

        response_text = await run_agent(
            user_id=incoming.user_id,
            session_id=incoming.chat_id,
            message=incoming.text or "",
        )
        await _whatsapp_adapter.send_message(incoming.chat_id, response_text)

        # Increment counter after successful response
        await _wa_increment_rate_counter(incoming.chat_id)
    except Exception as exc:
        logger.error(
            "whatsapp.processing_error",
            chat_id=incoming.chat_id,
            error=str(exc),
        )
        await _whatsapp_adapter.send_message(
            incoming.chat_id,
            "Desculpe, ocorreu um erro ao processar sua mensagem. Tente novamente.",
        )

    return JSONResponse({"status": "processed"})


async def _wa_check_rate_limit(chat_id: str) -> dict:
    """Check rate limit via premium plugin (fail-open if not installed)."""
    try:
        from premium.billing.rate_limiter import check_chat_rate_limit
        from channels.telegram.webhook import _get_eleitor_plano

        plano = await _get_eleitor_plano(chat_id)
        return await check_chat_rate_limit(chat_id, plano)
    except ImportError:
        return {"allowed": True, "remaining": None, "limit": None, "reset_at": None}
    except Exception:
        logger.debug("whatsapp.rate_limit.check_failed", exc_info=True)
        return {"allowed": True, "remaining": None, "limit": None, "reset_at": None}


async def _wa_increment_rate_counter(chat_id: str) -> None:
    """Increment rate limit counter via premium plugin."""
    try:
        from premium.billing.rate_limiter import increment_chat_counter
        from channels.telegram.webhook import _get_eleitor_plano

        plano = await _get_eleitor_plano(chat_id)
        await increment_chat_counter(chat_id, plano)
    except ImportError:
        pass
    except Exception:
        logger.debug("whatsapp.rate_limit.increment_failed", exc_info=True)


def _wa_format_rate_limit_msg(rate_result: dict) -> str:
    """Format rate limit message for WhatsApp user."""
    try:
        from premium.billing.rate_limiter import format_rate_limit_message
        return format_rate_limit_message(
            rate_result.get("remaining"), rate_result.get("limit"), rate_result.get("reset_at")
        )
    except ImportError:
        return "⚠️ Limite diário atingido. Tente novamente amanhã."
