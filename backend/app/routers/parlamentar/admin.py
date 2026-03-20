"""Admin endpoints for managing parlamentar dashboard users and invitations.

All endpoints require the authenticated user to have `is_admin=True`.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.exceptions import UnauthorizedException
from app.logging import get_logger
from app.routers.parlamentar.auth import get_current_parlamentar_user
from app.schemas.parlamentar import (
    AdminConviteListItem,
    AdminUserUpdateRequest,
    ConviteCreateRequest,
    ConviteCreateResponse,
    ParlamentarUserResponse,
)
from app.services.parlamentar_auth_service import ParlamentarAuthService

logger = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["parlamentar-admin"])


async def get_current_admin_user(
    current_user: ParlamentarUserResponse = Depends(get_current_parlamentar_user),
) -> ParlamentarUserResponse:
    """Dependency that ensures the authenticated user is an admin."""
    if not current_user.is_admin:
        raise UnauthorizedException("Acesso restrito a administradores.")
    return current_user


# ─── Users ──────────────────────────────────────────


@router.get("/users", response_model=list[ParlamentarUserResponse])
async def list_users(
    tipo: str | None = None,
    ativo: bool | None = None,
    _admin: ParlamentarUserResponse = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> list[ParlamentarUserResponse]:
    """List all parlamentar users with optional filters."""
    service = ParlamentarAuthService(db)
    users = await service.list_users(tipo=tipo, ativo=ativo)
    return [ParlamentarUserResponse.model_validate(u) for u in users]


@router.put("/users/{user_id}", response_model=ParlamentarUserResponse)
async def update_user(
    user_id: str,
    body: AdminUserUpdateRequest,
    _admin: ParlamentarUserResponse = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> ParlamentarUserResponse:
    """Update a parlamentar user (admin action)."""
    service = ParlamentarAuthService(db)
    user = await service.admin_update_user(
        user_id=user_id,
        nome=body.nome,
        cargo=body.cargo,
        tipo=body.tipo,
        ativo=body.ativo,
        is_admin=body.is_admin,
        deputado_id=body.deputado_id,
    )
    return ParlamentarUserResponse.model_validate(user)


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    _admin: ParlamentarUserResponse = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a parlamentar user permanently."""
    service = ParlamentarAuthService(db)
    await service.delete_user(user_id)


# ─── Invitations ────────────────────────────────────


@router.get("/convites", response_model=list[AdminConviteListItem])
async def list_invitations(
    _admin: ParlamentarUserResponse = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> list[AdminConviteListItem]:
    """List all pending invitations."""
    service = ParlamentarAuthService(db)
    invites = await service.list_pending_invites()
    return [AdminConviteListItem.model_validate(i) for i in invites]


@router.post("/convite", response_model=ConviteCreateResponse, status_code=201)
async def create_invitation(
    body: ConviteCreateRequest,
    _admin: ParlamentarUserResponse = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> ConviteCreateResponse:
    """Create an invitation for a new parlamentar user (admin action)."""
    service = ParlamentarAuthService(db)
    user = await service.create_invitation(
        email=body.email,
        nome=body.nome,
        tipo=body.tipo,
        cargo=body.cargo,
        deputado_id=body.deputado_id,
    )
    return ConviteCreateResponse(
        user_id=str(user.id) if hasattr(user.id, "hex") else user.id,
        email=user.email,
        codigo_convite=user.codigo_convite or "",
    )


@router.get("/stats")
async def admin_stats(
    _admin: ParlamentarUserResponse = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return summary statistics for the admin dashboard."""
    service = ParlamentarAuthService(db)
    return await service.count_users()


# ─── Webhooks (outbound) ───────────────────────────


@router.get("/webhooks")
async def list_admin_webhooks(
    _admin: ParlamentarUserResponse = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List all outbound webhook subscriptions for admin dashboard."""
    from sqlalchemy import select

    from app.domain.assinatura import AssinaturaWebhook

    result = await db.execute(
        select(AssinaturaWebhook).order_by(AssinaturaWebhook.data_criacao.desc())
    )
    webhooks = result.scalars().all()
    return [
        {
            "id": str(wh.id),
            "nome": wh.nome,
            "url": wh.url,
            "eventos": wh.eventos,
            "ativo": wh.ativo,
            "falhas_consecutivas": wh.falhas_consecutivas,
            "ultimo_dispatch": wh.ultimo_dispatch.isoformat() if wh.ultimo_dispatch else None,
            "data_criacao": wh.data_criacao.isoformat() if wh.data_criacao else None,
        }
        for wh in webhooks
    ]


@router.post("/webhooks/{webhook_id}/reactivate")
async def reactivate_admin_webhook(
    webhook_id: str,
    _admin: ParlamentarUserResponse = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Reactivate a webhook and reset its failure counter."""
    import uuid as _uuid

    from app.services.publicacao_service import PublicacaoService

    service = PublicacaoService(db)
    webhook = await service.get_webhook_by_id(_uuid.UUID(webhook_id))
    webhook.ativo = True
    webhook.falhas_consecutivas = 0
    await db.flush()
    return {"status": "reactivated", "id": webhook_id}
