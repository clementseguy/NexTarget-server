from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, validator

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserPublic(BaseModel):
    id: str
    email: EmailStr
    is_active: bool
    provider: str
    display_name: Optional[str]
    avatar_url: Optional[str]
    experience_level: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True

class UserProfileUpdate(BaseModel):
    """Request schema for updating user profile."""
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    experience_level: Optional[str] = None

    @validator("experience_level")
    def validate_experience(cls, v):
        if v is not None and v not in ("beginner", "advanced", "expert"):
            raise ValueError("Must be beginner, advanced, or expert")
        return v
