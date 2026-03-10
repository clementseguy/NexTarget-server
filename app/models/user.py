from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, UniqueConstraint
import uuid

class User(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("email", "provider", name="uix_email_provider"),)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True)
    email: str = Field(index=True)
    provider: str = Field(index=True)  # 'google', 'facebook'
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Profile (from IdP + user choice)
    display_name: Optional[str] = Field(default=None)
    display_name_custom: bool = Field(default=False)  # True if user has manually set their name
    avatar_url: Optional[str] = Field(default=None)    # URL from IdP, refreshed on login
    experience_level: Optional[str] = Field(default=None)  # beginner | advanced | expert
