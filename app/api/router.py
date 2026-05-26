from fastapi import APIRouter

from app.api.auth_routes import router as auth_router
from app.api.claims import router as claims_router
from app.api.multi_agent_routes import router as multi_agent_router

api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(claims_router, tags=["claims"])
api_router.include_router(multi_agent_router, tags=["multi-agent-audit"])
