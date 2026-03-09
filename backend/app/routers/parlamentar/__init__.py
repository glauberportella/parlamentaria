"""Parlamentar dashboard routers package."""

from fastapi import APIRouter

from app.routers.parlamentar.auth import router as auth_router
from app.routers.parlamentar.dashboard import router as dashboard_router
from app.routers.parlamentar.proposicoes import router as proposicoes_router
from app.routers.parlamentar.votos import router as votos_router

router = APIRouter(prefix="/parlamentar", tags=["parlamentar"])

router.include_router(auth_router)
router.include_router(dashboard_router)
router.include_router(proposicoes_router)
router.include_router(votos_router)
