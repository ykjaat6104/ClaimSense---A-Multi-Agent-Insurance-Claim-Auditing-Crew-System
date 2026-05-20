from collections.abc import Generator

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_session
from app.services.auth_token import verify_access_token

security = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    yield from get_session()


def get_current_username(
    creds: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Not authenticated")
    settings = get_settings()
    sub = verify_access_token(creds.credentials, settings.claimsense_auth_secret)
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return sub
