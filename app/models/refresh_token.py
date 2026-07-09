from datetime import datetime
from typing import Optional
import uuid

from sqlmodel import SQLModel, Field


class RefreshToken(SQLModel, table=True):
    """Refresh token record (NT-048).

    Only the SHA-256 hash of the token is stored — never the raw value.
    Tokens belong to a rotation *family*: each refresh revokes the current
    token and issues a new one in the same family. If a revoked token is
    presented again (theft/replay), the whole family is revoked.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(index=True)
    token_hash: str = Field(index=True, unique=True)
    family_id: str = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    revoked_at: Optional[datetime] = Field(default=None)
