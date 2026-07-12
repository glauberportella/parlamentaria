"""Subscription management endpoints — RSS and Webhooks."""

import uuid

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_db
from app.exceptions import NotFoundException, UnauthorizedException
from app.schemas.assinatura import (
    AssinaturaRSSCreate,
    AssinaturaRSSResponse,
    AssinaturaWebhookCreate,
    AssinaturaWebhookResponse,
)
from app.services.publicacao_service import PublicacaoService
from app.logging import get_logger

router = APIRouter(prefix="/assinaturas", tags=["assinaturas"])

logger = get_logger(__name__)


async def verify_api_key(x_api_key: str = Header(...)) -> str:
    """Validate the admin API key from the request header."""
    if x_api_key != settings.admin_api_key:
        raise UnauthorizedException("API key inválida")
    return x_api_key


# ------------------------------------------------------------------
# RSS Subscriptions
# ------------------------------------------------------------------


@router.post("/rss", response_model=AssinaturaRSSResponse, dependencies=[Depends(verify_api_key)])
async def create_rss_subscription(
    data: AssinaturaRSSCreate,
    db: AsyncSession = Depends(get_db),
) -> AssinaturaRSSResponse:
    """Create a new RSS feed subscription. Returns token for feed access."""
    service = PublicacaoService(db)
    assinatura = await service.create_rss_subscription(
        nome=data.nome,
        filtro_temas=data.filtro_temas,
        filtro_uf=data.filtro_uf,
        email=data.email,
    )
    return AssinaturaRSSResponse.model_validate(assinatura)


@router.get("/rss/{subscription_id}", response_model=AssinaturaRSSResponse, dependencies=[Depends(verify_api_key)])
async def get_rss_subscription(
    subscription_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> AssinaturaRSSResponse:
    """Get details of an RSS subscription."""
    service = PublicacaoService(db)
    assinatura = await service.get_rss_by_id(subscription_id)
    if not assinatura:
        raise NotFoundException(f"Assinatura RSS {subscription_id} não encontrada")
    return AssinaturaRSSResponse.model_validate(assinatura)


@router.delete("/rss/{subscription_id}", dependencies=[Depends(verify_api_key)])
async def delete_rss_subscription(
    subscription_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Cancel an RSS subscription."""
    service = PublicacaoService(db)
    await service.delete_rss(subscription_id)
    return {"status": "deleted"}


# ------------------------------------------------------------------
# Webhook Subscriptions
# ------------------------------------------------------------------


@router.post("/webhooks", response_model=AssinaturaWebhookResponse, dependencies=[Depends(verify_api_key)])
async def create_webhook_subscription(
    data: AssinaturaWebhookCreate,
    db: AsyncSession = Depends(get_db),
) -> AssinaturaWebhookResponse:
    """Register a new outbound webhook subscription."""
    import uuid as _uuid
    service = PublicacaoService(db)
    secret = _uuid.uuid4().hex  # Auto-generate HMAC secret
    assinatura = await service.create_webhook_subscription(
        nome=data.nome,
        url=data.url,
        secret=secret,
        eventos=data.eventos,
        filtro_temas=data.filtro_temas,
    )
    return AssinaturaWebhookResponse.model_validate(assinatura)


@router.get("/webhooks/{subscription_id}", response_model=AssinaturaWebhookResponse, dependencies=[Depends(verify_api_key)])
async def get_webhook_subscription(
    subscription_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> AssinaturaWebhookResponse:
    """Get details of a webhook subscription."""
    service = PublicacaoService(db)
    assinatura = await service.get_webhook_by_id(subscription_id)
    if not assinatura:
        raise NotFoundException(f"Assinatura Webhook {subscription_id} não encontrada")
    return AssinaturaWebhookResponse.model_validate(assinatura)


@router.delete("/webhooks/{subscription_id}", dependencies=[Depends(verify_api_key)])
async def delete_webhook_subscription(
    subscription_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Remove a webhook subscription."""
    service = PublicacaoService(db)
    await service.delete_webhook(subscription_id)
    return {"status": "deleted"}


@router.post("/webhooks/{subscription_id}/test", dependencies=[Depends(verify_api_key)])
async def test_webhook(
    subscription_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Dispatch a test payload to the given webhook endpoint."""
    service = PublicacaoService(db)
    assinatura = await service.get_webhook_by_id(subscription_id)
    if not assinatura:
        raise NotFoundException(f"Assinatura Webhook {subscription_id} não encontrada")

    test_payload = {
        "evento": "test",
        "timestamp": "2026-01-01T00:00:00-03:00",
        "mensagem": "Payload de teste da Parlamentaria",
    }
    success = await service.dispatch_webhook(assinatura, test_payload)
    status = "delivered" if success else "failed"
    logger.info("assinatura.webhook.test", subscription_id=str(subscription_id), status=status)
    return {"status": status}


# ------------------------------------------------------------------
# Admin: List all webhooks + reactivate
# ------------------------------------------------------------------


@router.get("/webhooks", response_model=list[AssinaturaWebhookResponse], dependencies=[Depends(verify_api_key)])
async def list_webhooks(
    db: AsyncSession = Depends(get_db),
) -> list[AssinaturaWebhookResponse]:
    """List all webhook subscriptions (admin)."""
    from sqlalchemy import select
    from app.domain.assinatura import AssinaturaWebhook

    result = await db.execute(
        select(AssinaturaWebhook).order_by(AssinaturaWebhook.data_criacao.desc())
    )
    webhooks = result.scalars().all()
    return [AssinaturaWebhookResponse.model_validate(wh) for wh in webhooks]


@router.post("/webhooks/{subscription_id}/reactivate", dependencies=[Depends(verify_api_key)])
async def reactivate_webhook(
    subscription_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> AssinaturaWebhookResponse:
    """Reactivate a webhook subscription and reset failure counter."""
    service = PublicacaoService(db)
    webhook = await service.get_webhook_by_id(subscription_id)
    webhook.ativo = True
    webhook.falhas_consecutivas = 0
    await db.flush()
    await db.refresh(webhook)
    logger.info("assinatura.webhook.reactivated", id=str(subscription_id))
    return AssinaturaWebhookResponse.model_validate(webhook)
