from pydantic import BaseModel, EmailStr

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
