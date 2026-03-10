from fastapi import APIRouter, Depends
from sqlmodel import Session

from ..schemas.auth import UserPublic, UserProfileUpdate
from ..models.user import User
from ..services.database import get_session
from .deps import get_current_user

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserPublic)
async def read_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me/profile", response_model=UserPublic)
async def update_profile(
    update: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Update current user's profile information.
    
    Updatable fields:
    - display_name: User's preferred display name (1-100 chars), null to reset to IdP value
    - experience_level: beginner, advanced, or expert, null to unset
    
    Args:
        update: Profile fields to update
        current_user: Authenticated user
        session: Database session
        
    Returns:
        Updated user profile
    """
    update_data = update.dict(exclude_unset=True)
    
    if not update_data:
        return current_user
    
    if "display_name" in update_data:
        current_user.display_name = update_data["display_name"]
        # Mark as custom if user sets a value, reset if null (revert to IdP on next login)
        current_user.display_name_custom = update_data["display_name"] is not None
    
    if "experience_level" in update_data:
        current_user.experience_level = update_data["experience_level"]
    
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    
    return current_user
