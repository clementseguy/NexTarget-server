from datetime import datetime
from sqlmodel import SQLModel, Field, UniqueConstraint
import uuid
from typing import Optional

class User(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("email", "provider", name="uix_email_provider"),)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True)
    email: str = Field(index=True)
    provider: str = Field(default="local", index=True)  # 'local', 'google', ...
    hashed_password: Optional[str] = Field(default=None, nullable=True)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
