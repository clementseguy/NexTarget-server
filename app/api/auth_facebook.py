"""
Facebook OAuth 2.0 authentication endpoints.
Implements the authorization code flow with Graph API.
"""
from urllib.parse import urlencode
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlmodel import Session
import httpx

from ..core.config import get_settings
from ..core.oauth_config import (
    FACEBOOK_AUTH_ENDPOINT,
    FACEBOOK_TOKEN_ENDPOINT,
    FACEBOOK_USERINFO_ENDPOINT,
    FACEBOOK_SCOPES,
    OAUTH_TIMEOUT_SECONDS,
)
from ..services.oauth_state import get_state_manager
from ..services.database import get_session
from .oauth_utils import (
    get_or_create_user,
    generate_token_response,
    assert_provider_configured,
)


router = APIRouter(prefix="/auth/facebook", tags=["auth-facebook"])
settings = get_settings()


@router.get("/start")
def facebook_auth_start(
    session_nonce: str = Query(
        None,
        description="Opaque value from client to bind session"
    )
) -> dict:
    """
    Initiate Facebook OAuth 2.0 authorization flow.
    
    Args:
        session_nonce: Optional client nonce for session binding
        
    Returns:
        Dictionary with auth_url and state for client redirect
        
    Raises:
        HTTPException: If Facebook OAuth is not configured
    """
    assert_provider_configured(
        settings.facebook_client_id,
        settings.facebook_client_secret,
        settings.facebook_redirect_uri,
        "Facebook"
    )
    
    state_manager = get_state_manager()
    state, _ = state_manager.create_state(client_nonce=session_nonce)
    
    params = {
        "client_id": settings.facebook_client_id,
        "redirect_uri": settings.facebook_redirect_uri,
        "state": state,
        "response_type": "code",
        "scope": ",".join(FACEBOOK_SCOPES),
    }
    
    auth_url = f"{FACEBOOK_AUTH_ENDPOINT}?{urlencode(params)}"
    
    return {
        "auth_url": auth_url,
        "state": state,
    }


@router.get("/callback")
async def facebook_auth_callback(
    code: str,
    state: str,
    session: Session = Depends(get_session)
) -> RedirectResponse:
    """
    Handle Facebook OAuth callback and exchange code for tokens.
    
    Args:
        code: Authorization code from Facebook
        state: State token for CSRF protection
        session: Database session
        
    Returns:
        Dictionary with access_token, token_type, email, and provider
        
    Raises:
        HTTPException: If state is invalid, token exchange fails, or user creation fails
    """
    assert_provider_configured(
        settings.facebook_client_id,
        settings.facebook_client_secret,
        settings.facebook_redirect_uri,
        "Facebook"
    )
    
    # Verify and consume state token (CSRF protection)
    state_manager = get_state_manager()
    stored_state = state_manager.verify_and_consume(state)
    
    if not stored_state:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired state"
        )
    
    # Exchange authorization code for access token
    token_params = {
        "client_id": settings.facebook_client_id,
        "redirect_uri": settings.facebook_redirect_uri,
        "client_secret": settings.facebook_client_secret,
        "code": code,
    }
    
    async with httpx.AsyncClient(timeout=OAUTH_TIMEOUT_SECONDS) as client:
        token_response = await client.get(
            FACEBOOK_TOKEN_ENDPOINT,
            params=token_params
        )
    
    if token_response.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail=f"Token exchange failed: {token_response.text}"
        )
    
    token_payload = token_response.json()
    access_token = token_payload.get("access_token")
    
    if not access_token:
        raise HTTPException(
            status_code=400,
            detail="No access_token returned by Facebook"
        )
    
    # Fetch user information from Facebook Graph API
    user_params = {
        "fields": "id,email",
        "access_token": access_token,
    }
    
    async with httpx.AsyncClient(timeout=OAUTH_TIMEOUT_SECONDS) as client:
        user_response = await client.get(
            FACEBOOK_USERINFO_ENDPOINT,
            params=user_params
        )
    
    if user_response.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to fetch user info: {user_response.text}"
        )
    
    user_info = user_response.json()
    facebook_id = user_info.get("id")
    
    if not facebook_id:
        raise HTTPException(
            status_code=400,
            detail="Missing Facebook user id"
        )
    
    # Handle email (user can hide email permission)
    email = user_info.get("email") or f"fb_{facebook_id}@example.local"
    
    # Get or create user
    user = get_or_create_user(session, email, provider="facebook")
    
    # Generate JWT token and redirect to custom scheme for mobile app
    token_response = generate_token_response(user)
    token_response["provider"] = "facebook"  # Add provider to response
    
    # Build redirect URL with token in fragment (# not ? for security)
    callback_url = "nextarget://callback"
    fragment = urlencode(token_response)
    redirect_url = f"{callback_url}#{fragment}"
    
    return RedirectResponse(url=redirect_url, status_code=302)
