import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.config import get_settings
from app.db import crud
from app.middleware.rate_limit import limiter, RATE_LIMITS
from app.schemas.api import LoginRequest, LoginResponse, SignupRequest, SignupResponse
from app.services.auth_token import create_access_token, hash_password, verify_access_token, verify_password

logger = logging.getLogger(__name__)

router = APIRouter()
_security = HTTPBearer(auto_error=False)


@router.post("/login", response_model=LoginResponse)
@limiter.limit(RATE_LIMITS["auth"])
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    settings = get_settings()

    # Try demo credentials first (backward compatibility)
    if body.username == settings.claimsense_demo_user and body.password == settings.claimsense_demo_password:
        token = create_access_token(
            subject=body.username,
            secret=settings.claimsense_auth_secret,
            algorithm=settings.jwt_algorithm,
            expires_in_hours=settings.jwt_expiration_hours,
        )
        logger.info(f"Demo login for user: {body.username}")
        return LoginResponse(access_token=token, username=body.username, token_type="bearer")

    # Database-backed login for real users
    user = crud.get_user_by_username(db, body.username)
    if not user or not verify_password(body.password, user.hashed_password):
        logger.warning(f"Failed login attempt for user: {body.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        subject=user.username,
        secret=settings.claimsense_auth_secret,
        algorithm=settings.jwt_algorithm,
        expires_in_hours=settings.jwt_expiration_hours,
    )

    logger.info(f"Successful login for user: {body.username}")
    return LoginResponse(access_token=token, username=user.username, token_type="bearer")


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(RATE_LIMITS["auth"])
def signup(request: Request, body: SignupRequest, db: Session = Depends(get_db)) -> SignupResponse:
    settings = get_settings()

    # Check if username already exists
    existing = crud.get_user_by_username(db, body.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )

    # Reserve demo username
    if body.username == settings.claimsense_demo_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )

    # Create user
    hashed = hash_password(body.password)
    user = crud.create_user(db, username=body.username, hashed_password=hashed)

    # Issue JWT
    token = create_access_token(
        subject=user.username,
        secret=settings.claimsense_auth_secret,
        algorithm=settings.jwt_algorithm,
        expires_in_hours=settings.jwt_expiration_hours,
    )

    logger.info(f"New user signed up: {body.username}")
    return SignupResponse(access_token=token, username=user.username, token_type="bearer")


@router.get("/me")
def me(creds: HTTPAuthorizationCredentials | None = Depends(_security)) -> dict[str, str]:
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
