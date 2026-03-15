"""Repository for SocialPost domain model."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.social_post import RedeSocial, SocialPost, StatusPost, TipoPostSocial
from app.repositories.base import BaseRepository


class SocialPostRepository(BaseRepository[SocialPost]):
    """Data access for social media posts."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(SocialPost, session)

    async def find_by_status(
        self,
        status: StatusPost,
        offset: int = 0,
        limit: int = 50,
    ) -> Sequence[SocialPost]:
        """Find posts by status."""
        stmt = (
            select(SocialPost)
            .where(SocialPost.status == status)
            .order_by(SocialPost.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def find_by_rede(
        self,
        rede: RedeSocial,
        offset: int = 0,
        limit: int = 50,
    ) -> Sequence[SocialPost]:
        """Find posts by social network."""
        stmt = (
            select(SocialPost)
            .where(SocialPost.rede == rede)
            .order_by(SocialPost.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def find_by_tipo(
        self,
        tipo: TipoPostSocial,
        offset: int = 0,
        limit: int = 50,
    ) -> Sequence[SocialPost]:
        """Find posts by type."""
        stmt = (
            select(SocialPost)
            .where(SocialPost.tipo == tipo)
            .order_by(SocialPost.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_filtered(
        self,
        rede: RedeSocial | None = None,
        tipo: TipoPostSocial | None = None,
        status: StatusPost | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[Sequence[SocialPost], int]:
        """List posts with optional filters. Returns (items, total)."""
        base: Select = select(SocialPost)
        count_stmt = select(func.count()).select_from(SocialPost)

        if rede is not None:
            base = base.where(SocialPost.rede == rede)
            count_stmt = count_stmt.where(SocialPost.rede == rede)
        if tipo is not None:
            base = base.where(SocialPost.tipo == tipo)
            count_stmt = count_stmt.where(SocialPost.tipo == tipo)
        if status is not None:
            base = base.where(SocialPost.status == status)
            count_stmt = count_stmt.where(SocialPost.status == status)

        base = base.order_by(SocialPost.created_at.desc()).offset(offset).limit(limit)

        result = await self.session.execute(base)
        items = result.scalars().all()

        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar_one()

        return items, total

    async def exists_for_proposicao_rede_tipo(
        self,
        proposicao_id: int,
        rede: RedeSocial,
        tipo: TipoPostSocial,
    ) -> bool:
        """Check if a post already exists for this proposicao+rede+tipo."""
        stmt = (
            select(func.count())
            .select_from(SocialPost)
            .where(
                SocialPost.proposicao_id == proposicao_id,
                SocialPost.rede == rede,
                SocialPost.tipo == tipo,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    async def exists_for_comparativo_rede(
        self,
        comparativo_id: uuid.UUID,
        rede: RedeSocial,
    ) -> bool:
        """Check if a post already exists for this comparativo+rede."""
        stmt = (
            select(func.count())
            .select_from(SocialPost)
            .where(
                SocialPost.comparativo_id == comparativo_id,
                SocialPost.rede == rede,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    async def find_recent_published(
        self,
        hours: int = 48,
        limit: int = 100,
    ) -> Sequence[SocialPost]:
        """Find recently published posts (for metrics update)."""
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        stmt = (
            select(SocialPost)
            .where(
                SocialPost.status == StatusPost.PUBLICADO,
                SocialPost.publicado_em >= since,
            )
            .order_by(SocialPost.publicado_em.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_aggregated_metrics(self) -> dict:
        """Get aggregated metrics across all published posts."""
        stmt = select(
            func.count().label("total_posts"),
            func.count()
            .filter(SocialPost.status == StatusPost.PUBLICADO)
            .label("total_publicados"),
            func.count()
            .filter(SocialPost.status == StatusPost.FALHOU)
            .label("total_falhas"),
            func.coalesce(func.sum(SocialPost.likes), 0).label("total_likes"),
            func.coalesce(func.sum(SocialPost.shares), 0).label("total_shares"),
            func.coalesce(func.sum(SocialPost.comments), 0).label("total_comments"),
            func.coalesce(func.sum(SocialPost.impressions), 0).label(
                "total_impressions"
            ),
        )
        result = await self.session.execute(stmt)
        row = result.one()
        return {
            "total_posts": row.total_posts,
            "total_publicados": row.total_publicados,
            "total_falhas": row.total_falhas,
            "total_likes": row.total_likes,
            "total_shares": row.total_shares,
            "total_comments": row.total_comments,
            "total_impressions": row.total_impressions,
        }

    async def count_by_rede(self) -> dict[str, int]:
        """Count posts grouped by social network."""
        stmt = (
            select(SocialPost.rede, func.count().label("count"))
            .group_by(SocialPost.rede)
        )
        result = await self.session.execute(stmt)
        return {row.rede.value: row.count for row in result.all()}

    async def count_by_tipo(self) -> dict[str, int]:
        """Count posts grouped by type."""
        stmt = (
            select(SocialPost.tipo, func.count().label("count"))
            .group_by(SocialPost.tipo)
        )
        result = await self.session.execute(stmt)
        return {row.tipo.value: row.count for row in result.all()}
