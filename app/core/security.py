from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from typing import Dict, Any

from .config import get_settings

settings = get_settings()

# JWT tokens -----------------------------------------------------------------

def create_access_token(sub: str, expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_exp_minutes)
    expire = datetime.now(timezone.utc) + expires_delta
    payload = {"exp": expire, "sub": sub, "type": "access"}
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token


def decode_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
