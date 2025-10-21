"""
Common OAuth utilities for user management and token generation.
Shared code between different OAuth providers.
"""
from datetime import timedelta
from typing import Optional
from fastapi import HTTPException
from sqlmodel import Session, select

from ..models.user import User
from ..core.security import create_access_token, create_callback_token
from ..core.config import get_settings


def get_or_create_user(
    session: Session,
    email: str,
    provider: str
) -> User:
    """
    Get existing user or create new one for OAuth provider.
    
    Args:
        session: Database session
        email: User's email address
        provider: OAuth provider name (e.g., "google", "facebook")
        
    Returns:
        User instance (existing or newly created)
        
    Raises:
        HTTPException: If user creation fails
    """
    # Check if user exists
    user = session.exec(
        select(User).where(
            User.email == email,
            User.provider == provider
        )
    ).first()
    
    if user:
        return user
    
    # Create new user
    user = User(email=email, provider=provider)
    session.add(user)
    
    try:
        session.commit()
        session.refresh(user)
        return user
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create user: {str(e)}"
        )


def generate_token_response(user: User) -> dict:
    """
    Generate standardized OAuth token response.
    
    Args:
        user: Authenticated user
        
    Returns:
        Dictionary with access_token, token_type, email, and provider
    """
    settings = get_settings()
    
    jwt_token = create_access_token(
        sub=user.id,
        expires_delta=timedelta(minutes=settings.access_token_exp_minutes)
    )
    
    return {
        "access_token": jwt_token,
        "token_type": "bearer",
        "email": user.email,
        "provider": user.provider,
    }


def assert_provider_configured(
    client_id: Optional[str],
    client_secret: Optional[str],
    redirect_uri: Optional[str],
    provider_name: str
) -> None:
    """
    Validate that OAuth provider is properly configured.
    
    Args:
        client_id: OAuth client ID
        client_secret: OAuth client secret
        redirect_uri: OAuth redirect URI
        provider_name: Name of the provider (for error messages)
        
    Raises:
        HTTPException: If any required configuration is missing
    """
    if not (client_id and client_secret and redirect_uri):
        raise HTTPException(
            status_code=500,
            detail=f"{provider_name} OAuth not configured"
        )
