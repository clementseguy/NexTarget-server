from datetime import datetime, timedelta, timezone
from typing import Optional, Literal
import jwt
from typing import Dict, Any

from .config import get_settings

settings = get_settings()

# JWT tokens -----------------------------------------------------------------

def create_access_token(sub: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create a standard access token (default 60 minutes)."""
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_exp_minutes)
    expire = datetime.now(timezone.utc) + expires_delta
    payload = {"exp": expire, "sub": sub, "type": "access"}
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token


def create_callback_token(sub: str, provider: str, email: str) -> str:
    """Create a short-lived callback token (10 minutes) for OAuth redirect."""
    expires_delta = timedelta(minutes=settings.callback_token_exp_minutes)
    expire = datetime.now(timezone.utc) + expires_delta
    payload = {
        "exp": expire,
        "sub": sub,
        "type": "callback",
        "provider": provider,
        "email": email,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and verify any JWT token."""
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


def verify_callback_token(token: str) -> Dict[str, Any]:
    """Verify callback token and return payload if valid."""
    payload = decode_token(token)
    if payload.get("type") != "callback":
        raise jwt.InvalidTokenError("Invalid token type")
    return payload
