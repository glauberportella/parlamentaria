"""Webhook endpoints for messaging channels (Telegram, WhatsApp).

Telegram webhook processing is delegated to the channel adapter module.
WhatsApp remains a placeholder for future implementation.
"""

from fastapi import APIRouter, Request

from channels.telegram.webhook import router as telegram_router

router = APIRouter(tags=["webhooks"])

# Include the Telegram webhook router (handles /webhook/telegram)
router.include_router(telegram_router)


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request) -> dict:
    """Receive WhatsApp Business API webhook events (future).

    This endpoint is a placeholder. WhatsApp Business API integration
    is planned for a future phase.
    """
    _ = await request.body()
    return {"status": "received"}
