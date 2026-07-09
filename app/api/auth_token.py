"""
Token exchange endpoint for mobile OAuth flow.
Allows mobile apps to exchange short-lived callback tokens for long-lived access tokens.
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Response
from pydantic import BaseModel
from sqlmodel import Session
import jwt

from ..core.config import get_settings
from ..core.security import verify_callback_token, create_access_token
from ..services.database import get_session
from ..services.refresh_tokens import (
    RefreshTokenError,
    issue_refresh_token,
    revoke_refresh_token,
    rotate_refresh_token,
)
from ..models.user import User
from sqlmodel import select


router = APIRouter(prefix="/auth", tags=["auth-token"])


class TokenExchangeRequest(BaseModel):
    """Request to exchange callback token for access token."""
    callback_token: str


class TokenExchangeResponse(BaseModel):
    """Response with long-lived access token.

    NT-048: `refresh_token` / `refresh_expires_in` are additive fields —
    existing clients that ignore them keep working unchanged.
    """
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    email: str
    provider: str
    user_id: str
    refresh_token: Optional[str] = None
    refresh_expires_in: Optional[int] = None  # seconds


class TokenRefreshRequest(BaseModel):
    """Request to rotate a refresh token into a new token pair."""
    refresh_token: str


class TokenRevokeRequest(BaseModel):
    """Request to revoke a refresh token family (logout)."""
    refresh_token: str


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
        
        # Generate long-lived access token + refresh token (NT-048)
        settings = get_settings()
        access_token = create_access_token(sub=user.id)
        raw_refresh, _ = issue_refresh_token(session, user.id)

        return TokenExchangeResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.access_token_exp_minutes * 60,
            email=user.email,
            provider=user.provider,
            user_id=user.id,
            refresh_token=raw_refresh,
            refresh_expires_in=settings.refresh_token_exp_days * 24 * 3600,
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
    except HTTPException:
        raise
    except Exception:
        # No internal detail leaked to the client (AGENTS security rule 9).
        raise HTTPException(
            status_code=500,
            detail="Token exchange failed"
        )


@router.post("/token/refresh")
def refresh_access_token(
    request: TokenRefreshRequest,
    session: Session = Depends(get_session),
) -> TokenExchangeResponse:
    """Rotate a refresh token into a new access + refresh token pair (NT-048).

    The presented refresh token is consumed (single use). Presenting an
    already-consumed token is treated as a compromise signal: its whole
    rotation family is revoked and the client must re-login.

    Raises:
        HTTPException: 401 if the token is unknown, expired, revoked or reused.
    """
    try:
        raw_refresh, record = rotate_refresh_token(session, request.refresh_token)
    except RefreshTokenError as e:
        raise HTTPException(status_code=401, detail=str(e))

    user = session.exec(select(User).where(User.id == record.user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    settings = get_settings()
    return TokenExchangeResponse(
        access_token=create_access_token(sub=user.id),
        token_type="bearer",
        expires_in=settings.access_token_exp_minutes * 60,
        email=user.email,
        provider=user.provider,
        user_id=user.id,
        refresh_token=raw_refresh,
        refresh_expires_in=settings.refresh_token_exp_days * 24 * 3600,
    )


@router.post("/token/revoke", status_code=204)
def revoke_token(
    request: TokenRevokeRequest,
    session: Session = Depends(get_session),
) -> Response:
    """Revoke a refresh token and its whole family — logout (NT-048).

    Idempotent: always returns 204, whether or not the token exists
    (no token-existence oracle).
    """
    revoke_refresh_token(session, request.refresh_token)
    return Response(status_code=204)
