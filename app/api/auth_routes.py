import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings
from app.middleware.rate_limit import limiter, RATE_LIMITS
from app.schemas.api import LoginRequest, LoginResponse
from app.services.auth_token import create_access_token, verify_access_token

logger = logging.getLogger(__name__)

router = APIRouter()
_security = HTTPBearer(auto_error=False)


@router.post("/login", response_model=LoginResponse)
@limiter.limit(RATE_LIMITS["auth"])
def login(request: Request, body: LoginRequest) -> LoginResponse:
    """
    User login endpoint.
    
    Returns a JWT access token on successful authentication.
    Demo credentials are used for now; replace with database lookups in production.
    
    Rate limited to 5 attempts per minute.
    """
    settings = get_settings()
    
    # Validate credentials (currently demo-only)
    if body.username != settings.claimsense_demo_user or body.password != settings.claimsense_demo_password:
        logger.warning(f"Failed login attempt for user: {body.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create JWT token
    token = create_access_token(
        subject=body.username,
        secret=settings.claimsense_auth_secret,
        algorithm=settings.jwt_algorithm,
        expires_in_hours=settings.jwt_expiration_hours,
    )
    
    logger.info(f"Successful login for user: {body.username}")
    return LoginResponse(access_token=token, username=body.username, token_type="bearer")


@router.get("/me")
def me(creds: HTTPAuthorizationCredentials | None = Depends(_security)) -> dict[str, str]:
    """
    Get current authenticated user information.
    
    Requires a valid JWT token in the Authorization header.
    """
    if creds is None or creds.scheme.lower() != "bearer":
        logger.debug("Unauthorized access attempt: missing or invalid credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    settings = get_settings()
    sub = verify_access_token(
        creds.credentials,
        secret=settings.claimsense_auth_secret,
        algorithm=settings.jwt_algorithm,
    )
    
    if not sub:
        logger.debug("Unauthorized access attempt: invalid or expired token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {"username": sub}

