"""Pydantic schemas for parliamentarian dashboard auth and users."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Request to initiate Magic Link login."""

    email: EmailStr
    codigo_convite: str | None = Field(
        None, description="Código de convite para primeiro acesso"
    )


class LoginResponse(BaseModel):
    """Response after Magic Link email is dispatched."""

    message: str = "Se o email estiver cadastrado, você receberá um link de acesso."


class VerifyTokenRequest(BaseModel):
    """Request to verify a Magic Link token and exchange for JWT."""

    token: str


class AuthTokens(BaseModel):
    """JWT token pair returned on successful verification."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token TTL in seconds")


class RefreshTokenRequest(BaseModel):
    """Request to refresh an access token."""

    refresh_token: str


class ParlamentarUserResponse(BaseModel):
    """Public representation of a parlamentar dashboard user."""

    id: str  # UUID as string
    deputado_id: int | None = None
    email: str
    nome: str
    cargo: str | None = None
    tipo: str
    ativo: bool
    temas_acompanhados: list[str] | None = None
    notificacoes_email: bool
    ultimo_login: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def model_validate(cls, obj, **kwargs):
        """Override to handle UUID → str conversion from SQLAlchemy models."""
        import uuid as _uuid
        if hasattr(obj, "id") and isinstance(obj.id, _uuid.UUID):
            obj.__dict__["id"] = str(obj.id)
        return super().model_validate(obj, **kwargs)


class VerifyResponse(BaseModel):
    """Response after Magic Link token verification."""

    user: ParlamentarUserResponse
    tokens: AuthTokens


class ConviteCreateRequest(BaseModel):
    """Request to create an invitation for a new parlamentar user."""

    email: EmailStr
    nome: str
    cargo: str | None = None
    tipo: str = "ASSESSOR"
    deputado_id: int | None = None


class ConviteCreateResponse(BaseModel):
    """Response after invitation creation."""

    user_id: str
    email: str
    codigo_convite: str
    message: str = "Convite criado com sucesso."
