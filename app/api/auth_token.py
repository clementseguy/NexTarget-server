"""
Token exchange endpoint for mobile OAuth flow.
Allows mobile apps to exchange short-lived callback tokens for long-lived access tokens.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlmodel import Session
import jwt

from ..core.security import verify_callback_token, create_access_token
from ..services.database import get_session
from ..models.user import User
from sqlmodel import select


router = APIRouter(prefix="/auth", tags=["auth-token"])


class TokenExchangeRequest(BaseModel):
    """Request to exchange callback token for access token."""
    callback_token: str


class TokenExchangeResponse(BaseModel):
    """Response with long-lived access token."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    email: str
    provider: str
    user_id: str


@router.post("/token/exchange")
def exchange_callback_token(
    request: TokenExchangeRequest,
    session: Session = Depends(get_session),
) -> TokenExchangeResponse:
    """
    Exchange short-lived callback token for long-lived access token.
    
    Mobile flow:
    1. App receives callback: nextarget://callback?token=SHORT_LIVED_JWT
    2. App extracts token and calls this endpoint
    3. Backend validates callback token (10 min TTL)
    4. Backend returns long-lived access token (60 min TTL)
    5. App stores access token for API calls
    
    Args:
        request: Contains the callback_token from OAuth redirect
        session: Database session
        
    Returns:
        TokenExchangeResponse with long-lived access token
        
    Raises:
        HTTPException: If callback token is invalid, expired, or user not found
    """
    try:
        # Verify callback token
        payload = verify_callback_token(request.callback_token)
        
        user_id = payload.get("sub")
        email = payload.get("email")
        provider = payload.get("provider")
        
        if not user_id or not email or not provider:
            raise HTTPException(
                status_code=400,
                detail="Invalid callback token payload"
            )
        
        # Verify user exists in database
        user = session.exec(
            select(User).where(User.id == user_id)
        ).first()
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=404,
                detail="User not found or inactive"
            )
        
        # Generate long-lived access token
        access_token = create_access_token(sub=user.id)
        
        return TokenExchangeResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=60 * 60,  # 60 minutes in seconds
            email=user.email,
            provider=user.provider,
            user_id=user.id,
        )
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Callback token has expired"
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid callback token: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Token exchange failed: {str(e)}"
        )
