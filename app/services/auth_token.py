"""JWT-based authentication for ClaimSense."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from passlib.context import CryptContext

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    *,
    subject: str,
    secret: str,
    algorithm: str = "HS256",
    expires_in_hours: int = 24 * 7,
) -> str:
    """
    Create a JWT access token.
    
    Args:
        subject: Usually the username
        secret: Secret key for signing
        algorithm: JWT algorithm (default: HS256)
        expires_in_hours: Token expiration time in hours
    
    Returns:
        JWT token as string
    """
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=expires_in_hours)
    
    payload = {
        "sub": subject,
        "iat": now,
        "exp": expires,
        "type": "access",
    }
    
    token = jwt.encode(payload, secret, algorithm=algorithm)
    return token


def verify_access_token(
    token: str,
    secret: str,
    algorithm: str = "HS256",
) -> Optional[str]:
    """
    Verify a JWT access token and extract the subject (username).
    
    Args:
        token: JWT token to verify
        secret: Secret key used for signing
        algorithm: JWT algorithm (default: HS256)
    
    Returns:
        The subject (username) if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, secret, algorithms=[algorithm])
        
        # Validate token type
        if payload.get("type") != "access":
            logger.warning("Invalid token type in JWT")
            return None
        
        subject = payload.get("sub")
        if not subject:
            logger.warning("No subject in JWT")
            return None
        
        return str(subject)
    
    except jwt.ExpiredSignatureError:
        logger.debug("JWT token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error verifying JWT: {e}")
        return None
