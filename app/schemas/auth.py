from pydantic import BaseModel, EmailStr, root_validator
from typing import Optional

class RegisterRequest(BaseModel):
    email: EmailStr
    password: Optional[str] = None
    provider: str = "local"

    @root_validator
    def password_required_for_local(cls, values):
        provider = values.get("provider", "local")
        password = values.get("password")
        if provider == "local" and not password:
            raise ValueError("Password required for local provider")
        return values

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    provider: str = "local"

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserPublic(BaseModel):
    id: str
    email: EmailStr
    is_active: bool
    provider: str

    class Config:
        from_attributes = True
