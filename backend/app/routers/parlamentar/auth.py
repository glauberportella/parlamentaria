"""Authentication endpoints for the parliamentarian dashboard.

Handles Magic Link login, token verification, token refresh, and invitations.
"""

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_db
from app.exceptions import UnauthorizedException, ValidationException
from app.logging import get_logger
from app.schemas.parlamentar import (
    AuthTokens,
    ConviteCreateRequest,
    ConviteCreateResponse,
    DemoStatusResponse,
    LoginRequest,
    LoginResponse,
    ParlamentarUserResponse,
    ParlamentarUserUpdate,
    RefreshTokenRequest,
    VerifyResponse,
    VerifyTokenRequest,
)
from app.services.parlamentar_auth_service import ParlamentarAuthService

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["parlamentar-auth"])


async def get_current_parlamentar_user(
    authorization: str = Header(..., description="Bearer <access_token>"),
    db: AsyncSession = Depends(get_db),
) -> "ParlamentarUserResponse":
    """Dependency that validates JWT and returns the current parlamentar user."""
    if not authorization.startswith("Bearer "):
        raise UnauthorizedException("Token de autenticação ausente ou mal formatado.")

    token = authorization.removeprefix("Bearer ").strip()
    payload = ParlamentarAuthService.decode_token(token)

    if payload.get("type") != "access":
        raise UnauthorizedException("Token inválido para esta operação.")

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException("Token inválido.")

    service = ParlamentarAuthService(db)
    user = await service.get_user_by_id(user_id)
    if user is None or not user.ativo:
        raise UnauthorizedException("Conta não encontrada ou desativada.")

    return ParlamentarUserResponse.model_validate(user)


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Send a Magic Link email to the parlamentar user.

    Always returns success to prevent email enumeration.
    """
    service = ParlamentarAuthService(db)
    await service.request_magic_link(body.email, body.codigo_convite)
    return LoginResponse()


@router.post("/verify", response_model=VerifyResponse)
async def verify_token(
    body: VerifyTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> VerifyResponse:
    """Verify a Magic Link token and return JWT access + refresh tokens."""
    service = ParlamentarAuthService(db)
    user, access_token, refresh_token = await service.verify_magic_link(body.token)

    return VerifyResponse(
        user=ParlamentarUserResponse.model_validate(user),
        tokens=AuthTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.access_token_expire_minutes * 60,
        ),
    )


@router.post("/refresh", response_model=VerifyResponse)
async def refresh_token(
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> VerifyResponse:
    """Refresh an expired access token using a valid refresh token.

    Implements token rotation: a new refresh token is issued each time.
    """
    service = ParlamentarAuthService(db)
    user, access_token, new_refresh = await service.refresh_access_token(
        body.refresh_token
    )

    return VerifyResponse(
        user=ParlamentarUserResponse.model_validate(user),
        tokens=AuthTokens(
            access_token=access_token,
            refresh_token=new_refresh,
            expires_in=settings.access_token_expire_minutes * 60,
        ),
    )


@router.get("/me", response_model=ParlamentarUserResponse)
async def get_me(
    current_user: ParlamentarUserResponse = Depends(get_current_parlamentar_user),
) -> ParlamentarUserResponse:
    """Return the currently authenticated parlamentar user."""
    return current_user


@router.get("/demo-status", response_model=DemoStatusResponse)
async def demo_status() -> DemoStatusResponse:
    """Check whether demo login is available.

    Returns enabled=True when DEMO_MODE=true and not in production.
    """
    enabled = settings.demo_mode and not settings.is_production
    return DemoStatusResponse(enabled=enabled)


@router.post("/demo-login", response_model=VerifyResponse)
async def demo_login(
    db: AsyncSession = Depends(get_db),
) -> VerifyResponse:
    """Log in as the demo user (development/staging only).

    Creates the demo user automatically on first call.
    """
    service = ParlamentarAuthService(db)
    user, access_token, refresh_token = await service.demo_login()
    await db.commit()

    return VerifyResponse(
        user=ParlamentarUserResponse.model_validate(user),
        tokens=AuthTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.access_token_expire_minutes * 60,
        ),
    )


@router.put("/me", response_model=ParlamentarUserResponse)
async def update_me(
    body: ParlamentarUserUpdate,
    current_user: ParlamentarUserResponse = Depends(get_current_parlamentar_user),
    db: AsyncSession = Depends(get_db),
) -> ParlamentarUserResponse:
    """Update the authenticated parlamentar user's profile/preferences."""
    service = ParlamentarAuthService(db)
    updated = await service.update_user_profile(
        user_id=current_user.id,
        nome=body.nome,
        cargo=body.cargo,
        temas_acompanhados=body.temas_acompanhados,
        notificacoes_email=body.notificacoes_email,
    )
    return ParlamentarUserResponse.model_validate(updated)


@router.post(
    "/convite",
    response_model=ConviteCreateResponse,
    status_code=201,
)
async def create_invitation(
    body: ConviteCreateRequest,
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> ConviteCreateResponse:
    """Create an invitation for a new parlamentar user.

    Protected by admin API key.
    """
    if x_api_key != settings.admin_api_key:
        raise UnauthorizedException("API key inválida.")

    service = ParlamentarAuthService(db)
    user = await service.create_invitation(
        email=body.email,
        nome=body.nome,
        tipo=body.tipo,
        cargo=body.cargo,
        deputado_id=body.deputado_id,
        is_admin=body.is_admin,
    )

    return ConviteCreateResponse(
        user_id=user.id,
        email=user.email,
        codigo_convite=user.codigo_convite or "",
    )
