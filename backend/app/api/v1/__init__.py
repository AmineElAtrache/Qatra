from fastapi import APIRouter

from app.api.v1 import advisor, ask, auth, health, plots, recommendations, telegram, whatsapp

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(plots.router, prefix="/plots", tags=["plots"])
api_router.include_router(recommendations.router, prefix="/plots", tags=["recommendations"])
api_router.include_router(ask.router, prefix="/plots", tags=["ask"])
api_router.include_router(advisor.router, prefix="/advisor", tags=["advisor"])
api_router.include_router(telegram.router, prefix="/telegram", tags=["telegram"])
api_router.include_router(whatsapp.router, prefix="/whatsapp", tags=["whatsapp"])
