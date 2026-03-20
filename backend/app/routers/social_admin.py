"""Admin endpoints for social media management — protected by API key."""

from fastapi import APIRouter, Depends, Header, Path, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_db
from app.domain.social_post import RedeSocial, StatusPost, TipoPostSocial
from app.exceptions import NotFoundException, UnauthorizedException, ValidationException
from app.middleware import limiter
from app.repositories.social_post_repo import SocialPostRepository
from app.schemas.social_post import (
    SocialMetricsResponse,
    SocialPostListResponse,
    SocialPostResponse,
)
from app.services.social_media_service import SocialMediaService

router = APIRouter(prefix="/admin/social", tags=["admin-social"])


async def verify_api_key(x_api_key: str = Header(...)) -> str:
    """Validate the admin API key from the request header."""
    if x_api_key != settings.admin_api_key:
        raise UnauthorizedException("API key inválida")
    return x_api_key


@router.get("/posts", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
async def list_posts(
    request: Request,
    rede: RedeSocial | None = Query(None),
    tipo: TipoPostSocial | None = Query(None),
    status: StatusPost | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
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


@router.get("/posts/{post_id}", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
async def get_post(
    request: Request,
    post_id: str = Path(...),
    db: AsyncSession = Depends(get_db),
) -> SocialPostResponse:
    """Get a single social post detail."""
    import uuid

    from app.domain.social_post import SocialPost

    post = await db.get(SocialPost, uuid.UUID(post_id))
    if not post:
        raise NotFoundException("Post não encontrado")
    return SocialPostResponse.model_validate(post)


@router.post("/posts/{post_id}/approve", dependencies=[Depends(verify_api_key)])
@limiter.limit("10/minute")
async def approve_post(
    request: Request,
    post_id: str = Path(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Approve a draft post for publishing.

    If moderation is disabled, publishes immediately.
    Otherwise, marks as approved and dispatches publication task.
    """
    import uuid

    from app.domain.social_post import SocialPost

    post = await db.get(SocialPost, uuid.UUID(post_id))
    if not post:
        raise NotFoundException("Post não encontrado")
    if post.status != StatusPost.RASCUNHO:
        raise ValidationException(f"Post com status '{post.status.value}' não pode ser aprovado")

    service = SocialMediaService(db)
    await service.approve_post(uuid.UUID(post_id))
    await db.commit()

    # Dispatch async publication
    from app.tasks.social_media_tasks import publicar_post_aprovado_task

    publicar_post_aprovado_task.delay(post_id)

    return {"status": "approved", "post_id": post_id}


@router.post("/posts/{post_id}/cancel", dependencies=[Depends(verify_api_key)])
@limiter.limit("10/minute")
async def cancel_post(
    request: Request,
    post_id: str = Path(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Cancel a draft or approved post."""
    import uuid

    from app.domain.social_post import SocialPost

    post = await db.get(SocialPost, uuid.UUID(post_id))
    if not post:
        raise NotFoundException("Post não encontrado")
    if post.status in (StatusPost.PUBLICADO, StatusPost.CANCELADO):
        raise ValidationException(f"Post com status '{post.status.value}' não pode ser cancelado")

    service = SocialMediaService(db)
    await service.cancel_post(uuid.UUID(post_id))
    await db.commit()
    return {"status": "cancelled", "post_id": post_id}


@router.post("/posts/{post_id}/republish", dependencies=[Depends(verify_api_key)])
@limiter.limit("5/minute")
async def republish_post(
    request: Request,
    post_id: str = Path(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Re-attempt publishing a failed post."""
    import uuid

    from app.domain.social_post import SocialPost

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


@router.get("/metrics", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
async def get_metrics(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SocialMetricsResponse:
    """Get aggregated social media metrics."""
    repo = SocialPostRepository(db)
    metrics = await repo.get_aggregated_metrics()
    return SocialMetricsResponse(**metrics)


@router.post("/metrics/refresh", dependencies=[Depends(verify_api_key)])
@limiter.limit("5/minute")
async def refresh_metrics(request: Request) -> dict:
    """Trigger immediate metrics update for recent posts."""
    from app.tasks.social_media_tasks import atualizar_metricas_task

    atualizar_metricas_task.delay()
    return {"status": "queued"}


@router.get("/counts", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
async def get_counts(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get post counts by network and type."""
    repo = SocialPostRepository(db)
    by_rede = await repo.count_by_rede()
    by_tipo = await repo.count_by_tipo()
    return {"by_rede": by_rede, "by_tipo": by_tipo}
