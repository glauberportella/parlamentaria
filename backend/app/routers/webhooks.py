"""Webhook endpoints for messaging channels (Telegram, WhatsApp)."""

from fastapi import APIRouter, Request

router = APIRouter(prefix="/webhook", tags=["webhooks"])


@router.post("/telegram")
async def telegram_webhook(request: Request) -> dict:
    """Receive Telegram Bot API webhook updates."""
    # TODO: Validate webhook secret, parse update, dispatch to ADK Runner
    _ = await request.json()
    return {"status": "received"}


@router.post("/whatsapp")
async def whatsapp_webhook(request: Request) -> dict:
    """Receive WhatsApp Business API webhook events (future)."""
    # TODO: Implement WhatsApp webhook processing
    body = await request.body()
    return {"status": "received"}
