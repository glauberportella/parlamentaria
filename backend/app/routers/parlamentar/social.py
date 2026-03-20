"""Social media admin endpoints for parlamentar dashboard.

All endpoints require the authenticated user to have ``is_admin=True``.
Reuses the SocialPostRepository and SocialMediaService from the core backend.
"""

import uuid

from fastapi import APIRouter, Depends, Path, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.domain.social_post import RedeSocial, SocialPost, StatusPost, TipoPostSocial
from app.exceptions import NotFoundException, ValidationException
from app.middleware import limiter
from app.repositories.social_post_repo import SocialPostRepository
from app.routers.parlamentar.admin import get_current_admin_user
from app.schemas.parlamentar import ParlamentarUserResponse
from app.schemas.social_post import (
    SocialMetricsResponse,
    SocialPostListResponse,
    SocialPostResponse,
)
from app.services.social_media_service import SocialMediaService

router = APIRouter(prefix="/admin/social", tags=["parlamentar-admin-social"])


@router.get("/posts")
@limiter.limit("30/minute")
async def list_posts(
    request: Request,
    rede: RedeSocial | None = Query(None),
    tipo: TipoPostSocial | None = Query(None),
    status: StatusPost | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    _admin: ParlamentarUserResponse = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> SocialPostListResponse:
    """List social media posts with filters."""
    repo = SocialPostRepository(db)
    items, total = await repo.list_filtered(
        rede=rede, tipo=tipo, status=status, offset=offset, limit=limit,
    )
    return SocialPostListResponse(
        items=[SocialPostResponse.model_validate(p) for p in items],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/posts/{post_id}")
@limiter.limit("30/minute")
async def get_post(
    request: Request,
    post_id: str = Path(...),
    _admin: ParlamentarUserResponse = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> SocialPostResponse:
    """Get a single social post detail."""
    post = await db.get(SocialPost, uuid.UUID(post_id))
    if not post:
        raise NotFoundException("Post não encontrado")
    return SocialPostResponse.model_validate(post)


@router.post("/posts/{post_id}/approve")
@limiter.limit("10/minute")
async def approve_post(
    request: Request,
    post_id: str = Path(...),
    _admin: ParlamentarUserResponse = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Approve a draft post for publishing.

    Marks as approved and dispatches async publication task.
    """
    post = await db.get(SocialPost, uuid.UUID(post_id))
    if not post:
        raise NotFoundException("Post não encontrado")
    if post.status != StatusPost.RASCUNHO:
        raise ValidationException(f"Post com status '{post.status.value}' não pode ser aprovado")

    service = SocialMediaService(db)
    await service.approve_post(uuid.UUID(post_id))
    await db.commit()

    from app.tasks.social_media_tasks import publicar_post_aprovado_task

    publicar_post_aprovado_task.delay(post_id)

    return {"status": "approved", "post_id": post_id}


@router.post("/posts/{post_id}/reject")
@limiter.limit("10/minute")
async def reject_post(
    request: Request,
    post_id: str = Path(...),
    _admin: ParlamentarUserResponse = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Reject (cancel) a draft or approved post."""
    post = await db.get(SocialPost, uuid.UUID(post_id))
    if not post:
        raise NotFoundException("Post não encontrado")
    if post.status in (StatusPost.PUBLICADO, StatusPost.CANCELADO):
        raise ValidationException(f"Post com status '{post.status.value}' não pode ser rejeitado")

    service = SocialMediaService(db)
    await service.cancel_post(uuid.UUID(post_id))
    await db.commit()
    return {"status": "rejected", "post_id": post_id}


@router.post("/posts/{post_id}/republish")
@limiter.limit("5/minute")
async def republish_post(
    request: Request,
    post_id: str = Path(...),
    _admin: ParlamentarUserResponse = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Re-attempt publishing a failed post."""
    post = await db.get(SocialPost, uuid.UUID(post_id))
    if not post:
        raise NotFoundException("Post não encontrado")
    if post.status != StatusPost.FALHOU:
        raise ValidationException("Somente posts com status 'falhou' podem ser republicados")

    post.status = StatusPost.APROVADO
    post.erro = None
    await db.commit()

    from app.tasks.social_media_tasks import publicar_post_aprovado_task

    publicar_post_aprovado_task.delay(post_id)
    return {"status": "queued_for_republish", "post_id": post_id}


@router.get("/metrics")
@limiter.limit("30/minute")
async def get_metrics(
    request: Request,
    _admin: ParlamentarUserResponse = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> SocialMetricsResponse:
    """Get aggregated social media metrics."""
    repo = SocialPostRepository(db)
    metrics = await repo.get_aggregated_metrics()
    return SocialMetricsResponse(**metrics)


@router.get("/counts")
@limiter.limit("30/minute")
async def get_counts(
    request: Request,
    _admin: ParlamentarUserResponse = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get post counts by status, network and type."""
    repo = SocialPostRepository(db)
    by_rede = await repo.count_by_rede()
    by_tipo = await repo.count_by_tipo()

    # Count by status for the dashboard stats cards
    status_counts: dict[str, int] = {}
    for s in StatusPost:
        items, total = await repo.list_filtered(status=s, offset=0, limit=1)
        status_counts[s.value] = total

    return {"by_rede": by_rede, "by_tipo": by_tipo, "by_status": status_counts}
