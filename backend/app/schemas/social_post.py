"""Pydantic DTOs for SocialPost."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.social_post import RedeSocial, StatusPost, TipoPostSocial


class SocialPostCreate(BaseModel):
    """DTO for creating a social post."""

    tipo: TipoPostSocial
    rede: RedeSocial
    proposicao_id: int | None = None
    comparativo_id: uuid.UUID | None = None
    texto: str
    imagem_url: str | None = None
    imagem_path: str | None = None
    status: StatusPost = StatusPost.RASCUNHO


class SocialPostUpdate(BaseModel):
    """DTO for updating a social post."""

    texto: str | None = None
    imagem_url: str | None = None
    imagem_path: str | None = None
    status: StatusPost | None = None
    rede_post_id: str | None = None
    publicado_em: datetime | None = None
    erro: str | None = None
    likes: int | None = None
    shares: int | None = None
    comments: int | None = None
    impressions: int | None = None


class SocialPostResponse(BaseModel):
    """DTO for social post response."""

    id: uuid.UUID
    tipo: TipoPostSocial
    rede: RedeSocial
    proposicao_id: int | None = None
    comparativo_id: uuid.UUID | None = None
    texto: str
    imagem_url: str | None = None
    imagem_path: str | None = None
    status: StatusPost
    rede_post_id: str | None = None
    publicado_em: datetime | None = None
    erro: str | None = None
    likes: int = 0
    shares: int = 0
    comments: int = 0
    impressions: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SocialPostListResponse(BaseModel):
    """Paginated list of social posts."""

    items: list[SocialPostResponse]
    total: int
    offset: int
    limit: int


class SocialMetricsResponse(BaseModel):
    """Aggregated social media metrics."""

    total_posts: int = 0
    total_publicados: int = 0
    total_falhas: int = 0
    total_likes: int = 0
    total_shares: int = 0
    total_comments: int = 0
    total_impressions: int = 0
    posts_por_rede: dict[str, int] = Field(default_factory=dict)
    posts_por_tipo: dict[str, int] = Field(default_factory=dict)


class SocialPreviewRequest(BaseModel):
    """Request to generate a preview (text + image) without publishing."""

    tipo: TipoPostSocial
    rede: RedeSocial
    proposicao_id: int | None = None
    comparativo_id: uuid.UUID | None = None


class SocialPreviewResponse(BaseModel):
    """Preview response with generated text and image path."""

    texto: str
    imagem_path: str | None = None
    rede: RedeSocial
    tipo: TipoPostSocial
