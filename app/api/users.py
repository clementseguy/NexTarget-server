from fastapi import APIRouter, Depends

from ..schemas.auth import UserPublic
from ..models.user import User
from .deps import get_current_user

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserPublic)
async def read_me(current_user: User = Depends(get_current_user)):
    return current_user
