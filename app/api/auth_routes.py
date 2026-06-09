import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.api.deps import get_current_username, get_db
from app.config import get_settings
from app.db import crud
from app.middleware.rate_limit import limiter, RATE_LIMITS
from app.schemas.api import (
    LoginRequest,
    LoginResponse,
    ProfileResponse,
    SignupRequest,
    SignupResponse,
    UpdateProfileRequest,
)
from app.services.auth_token import create_access_token, hash_password, verify_access_token, verify_password

logger = logging.getLogger(__name__)

router = APIRouter()
_security = HTTPBearer(auto_error=False)

AVATAR_MAX_SIZE = 2 * 1024 * 1024
AVATAR_ALLOWED = {"image/jpeg", "image/png"}


@router.post("/login", response_model=LoginResponse)
@limiter.limit(RATE_LIMITS["auth"])
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    settings = get_settings()

    if body.username == settings.claimsense_demo_user and body.password == settings.claimsense_demo_password:
        token = create_access_token(
            subject=body.username,
            secret=settings.claimsense_auth_secret,
            algorithm=settings.jwt_algorithm,
            expires_in_hours=settings.jwt_expiration_hours,
        )
        logger.info(f"Demo login for user: {body.username}")
        return LoginResponse(access_token=token, username=body.username, token_type="bearer")

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

    existing = crud.get_user_by_username(db, body.username)
    if existing or body.username == settings.claimsense_demo_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )

    hashed = hash_password(body.password)
    user = crud.create_user(db, username=body.username, hashed_password=hashed, display_name=body.display_name)

    token = create_access_token(
        subject=user.username,
        secret=settings.claimsense_auth_secret,
        algorithm=settings.jwt_algorithm,
        expires_in_hours=settings.jwt_expiration_hours,
    )

    logger.info(f"New user signed up: {body.username}")
    return SignupResponse(access_token=token, username=user.username, display_name=user.display_name or user.username, token_type="bearer")


@router.get("/profile", response_model=ProfileResponse)
def get_profile(
    db: Session = Depends(get_db),
    username: str = Depends(get_current_username),
) -> ProfileResponse:
    user = crud.get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    avatar_url = None
    if user.avatar_path:
        avatar_path = Path(user.avatar_path)
        if avatar_path.exists():
            avatar_url = f"/avatars/{avatar_path.name}"

    return ProfileResponse(
        username=user.username,
        display_name=user.display_name,
        avatar_url=avatar_url,
        created_at=user.created_at.isoformat() if user.created_at else "",
    )


@router.put("/profile", response_model=ProfileResponse)
def update_profile(
    body: UpdateProfileRequest,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_username),
) -> ProfileResponse:
    user = crud.get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user = crud.update_user(db, user, display_name=body.display_name)

    avatar_url = None
    if user.avatar_path:
        avatar_path = Path(user.avatar_path)
        if avatar_path.exists():
            avatar_url = f"/avatars/{avatar_path.name}"

    return ProfileResponse(
        username=user.username,
        display_name=user.display_name,
        avatar_url=avatar_url,
        created_at=user.created_at.isoformat() if user.created_at else "",
    )


@router.post("/profile/avatar", response_model=dict)
async def upload_avatar(
    file: UploadFile,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_username),
) -> dict:
    if file.content_type not in AVATAR_ALLOWED:
        raise HTTPException(status_code=400, detail="Only JPEG and PNG images are allowed")

    contents = await file.read()
    if len(contents) > AVATAR_MAX_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds 2MB limit")

    user = crud.get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Delete old avatar if exists
    if user.avatar_path:
        old = Path(user.avatar_path)
        if old.exists():
            old.unlink()

    settings = get_settings()
    ext = "png" if file.content_type == "image/png" else "jpg"
    avatar_dir = settings.upload_dir / "avatars"
    avatar_dir.mkdir(parents=True, exist_ok=True)
    dest = avatar_dir / f"{uuid.uuid4()}.{ext}"
    dest.write_bytes(contents)

    crud.update_user_avatar(db, user, avatar_path=str(dest))

    return {"avatar_url": f"/avatars/{dest.name}"}


@router.delete("/profile/avatar", response_model=dict)
def delete_avatar(
    db: Session = Depends(get_db),
    username: str = Depends(get_current_username),
) -> dict:
    user = crud.get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.avatar_path:
        old = Path(user.avatar_path)
        if old.exists():
            old.unlink()
    crud.update_user_avatar(db, user, avatar_path="")

    return {"avatar_url": None}


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
