import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text

from app.api.router import api_router
from app.config import get_settings
from app.db.models import Base
from app.db.session import get_engine, get_session

logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    settings = get_settings()
    
    # Create required directories
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    (settings.upload_dir / "avatars").mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Starting ClaimSense (environment: {settings.environment})")
    logger.info(f"Upload directory: {settings.upload_dir}")
    logger.info(f"Reports directory: {settings.reports_dir}")
    
    # Create database tables (in production, use migrations instead)
    try:
        engine = get_engine()
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    yield
    
    logger.info("Shutting down ClaimSense")


# Initialize FastAPI app
settings = get_settings()

app = FastAPI(
    title="ClaimSense",
    description="AI-assisted insurance claim evaluation for adjusters: OCR, Gemini extraction, RAG, LangGraph agents.",
    version="0.2.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.is_development() else None,
    redoc_url="/api/redoc" if settings.is_development() else None,
    openapi_url="/api/openapi.json" if settings.is_development() else None,
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, lambda request, exc: JSONResponse(
    status_code=429,
    content={"detail": "Rate limit exceeded. Please try again later."},
))

# Add CORS middleware with hardened configuration
cors_origins = settings.get_cors_origins()
if settings.is_production():
    logger.warning(f"CORS configured for production with origins: {cors_origins}")
else:
    logger.info(f"CORS configured for development with origins: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=600,  # Cache preflight requests for 10 minutes
)

# Include API routers
app.include_router(api_router)

# Serve uploaded avatars
_avatars_dir = settings.upload_dir / "avatars"
if _avatars_dir.exists():
    app.mount("/avatars", StaticFiles(directory=str(_avatars_dir)), name="avatars")


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint with database connectivity validation."""
    try:
        # Test database connection
        session = next(get_session())
        session.execute(text("SELECT 1"))
        session.close()
        db_status = "ok"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = f"error: {str(e)}"
    
    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "product": "ClaimSense",
        "database": db_status,
    }


# SPA fallback routing for React Router
_dist = Path(__file__).resolve().parent.parent / "web" / "dist"


@app.get("/{full_path:path}")
async def spa_fallback(full_path: str) -> FileResponse:
    """
    Fallback route for SPA routing.
    Serves index.html for all non-API routes to allow React Router to handle navigation.
    """
    # Don't catch API routes or static assets with known extensions
    if full_path.startswith("api/") or "." in full_path.split("/")[-1]:
        from fastapi.exceptions import HTTPException
        raise HTTPException(status_code=404, detail="Not found")
    
    index_path = _dist / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    
    from fastapi.exceptions import HTTPException
    raise HTTPException(status_code=404, detail="SPA index not found")

