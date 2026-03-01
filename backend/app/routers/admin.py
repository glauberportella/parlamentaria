"""Admin endpoints — protected by API key."""

from fastapi import APIRouter, Depends, Header

from app.config import settings
from app.exceptions import UnauthorizedException

router = APIRouter(prefix="/admin", tags=["admin"])


async def verify_api_key(x_api_key: str = Header(...)) -> str:
    """Validate the admin API key from the request header."""
    if x_api_key != settings.admin_api_key:
        raise UnauthorizedException("API key inválida")
    return x_api_key


@router.get("/proposicoes", dependencies=[Depends(verify_api_key)])
async def list_proposicoes() -> dict[str, str]:
    """List synced proposições (admin only)."""
    # TODO: Implement with service layer
    return {"status": "not_implemented"}


@router.get("/eleitores", dependencies=[Depends(verify_api_key)])
async def list_eleitores() -> dict[str, str]:
    """List registered eleitores (admin only)."""
    # TODO: Implement with service layer
    return {"status": "not_implemented"}
