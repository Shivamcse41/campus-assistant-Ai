"""
app/auth/utils.py
──────────────────
Password hashing with bcrypt and JWT creation/verification.

Functions:
    hash_password(plain)           → hashed string
    verify_password(plain, hashed) → bool
    create_access_token(data)      → JWT string
    decode_access_token(token)     → TokenData

Note: Uses bcrypt directly (not passlib) to avoid the passlib 1.7.4 + bcrypt 5.x
      incompatibility where passlib crashes on startup with a 72-byte test password.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt
from fastapi import HTTPException, status

from app.config import settings
from app.auth.schemas import TokenData


# ── bcrypt password hashing ───────────────────────────────────────────────────

def hash_password(plain_password: str) -> str:
    """Hash a plain-text password using bcrypt. Never store plain passwords."""
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain-text password against a bcrypt hash.
    Returns True if they match, False otherwise.
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a signed JWT access token.

    Args:
        data:          Dict to encode (must include 'sub' and 'email')
        expires_delta: Custom expiry. Defaults to ACCESS_TOKEN_EXPIRE_MINUTES from settings.

    Returns:
        Encoded JWT string.
    """
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> TokenData:
    """
    Decode and validate a JWT token.

    Args:
        token: Raw JWT string (without 'Bearer ' prefix).

    Returns:
        TokenData with client_id and email.

    Raises:
        HTTPException 401: If token is invalid, expired, or malformed.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token. Please login again.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        client_id: str = payload.get("sub")
        email: str = payload.get("email")

        if client_id is None or email is None:
            raise credentials_exception

        return TokenData(client_id=client_id, email=email)

    except JWTError:
        raise credentials_exception
