from fastapi import APIRouter

from app.api.auth_routes import router as auth_router
from app.api.claims import router as claims_router

api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(claims_router, tags=["claims"])
