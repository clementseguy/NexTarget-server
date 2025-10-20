"""
Google OAuth 2.0 authentication endpoints.
Implements the authorization code flow with OIDC.
"""
from urllib.parse import urlencode
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlmodel import Session
import httpx
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from ..core.config import get_settings
from ..core.oauth_config import (
    GOOGLE_AUTH_ENDPOINT,
    GOOGLE_TOKEN_ENDPOINT,
    GOOGLE_SCOPES,
    OAUTH_TIMEOUT_SECONDS,
)
from ..services.oauth_state import get_state_manager
from ..services.database import get_session
from .oauth_utils import (
    get_or_create_user,
    generate_token_response,
    assert_provider_configured,
)


router = APIRouter(prefix="/auth/google", tags=["auth-google"])
settings = get_settings()


@router.get("/start")
def google_auth_start(
    session_nonce: str = Query(
        None,
        description="Opaque value from client to bind session"
    )
) -> dict:
    """
    Initiate Google OAuth 2.0 authorization flow.
    
    Args:
        session_nonce: Optional client nonce for session binding
        
    Returns:
        Dictionary with auth_url and state for client redirect
        
    Raises:
        HTTPException: If Google OAuth is not configured
    """
    assert_provider_configured(
        settings.google_client_id,
        settings.google_client_secret,
        settings.google_redirect_uri,
        "Google"
    )
    
    state_manager = get_state_manager()
    state, state_data = state_manager.create_state(client_nonce=session_nonce)
    
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": " ".join(GOOGLE_SCOPES),
        "state": state,
        "nonce": state_data["nonce"],
        "access_type": "offline",
        "prompt": "consent",
    }
    
    auth_url = f"{GOOGLE_AUTH_ENDPOINT}?{urlencode(params)}"
    
    return {
        "auth_url": auth_url,
        "state": state,
    }


@router.get("/callback")
async def google_auth_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="State token for CSRF protection"),
    session: Session = Depends(get_session),
) -> RedirectResponse:
    """
    Handle Google OAuth callback and exchange code for tokens.
    
    Args:
        code: Authorization code from Google
        state: State token for CSRF protection
        session: Database session
        
    Returns:
        Dictionary with access_token, token_type, email, and provider
        
    Raises:
        HTTPException: If state is invalid, token exchange fails, or user creation fails
    """
    assert_provider_configured(
        settings.google_client_id,
        settings.google_client_secret,
        settings.google_redirect_uri,
        "Google"
    )
    
    # Verify and consume state token (CSRF protection)
    state_manager = get_state_manager()
    stored_state = state_manager.verify_and_consume(state)
    
    if not stored_state:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired state"
        )
    
    # Exchange authorization code for tokens
    token_data = {
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": settings.google_redirect_uri,
        "grant_type": "authorization_code",
    }
    
    async with httpx.AsyncClient(timeout=OAUTH_TIMEOUT_SECONDS) as client:
        token_response = await client.post(
            GOOGLE_TOKEN_ENDPOINT,
            data=token_data
        )
    
    if token_response.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail=f"Token exchange failed: {token_response.text}"
        )
    
    token_payload = token_response.json()
    id_token_str = token_payload.get("id_token")
    
    if not id_token_str:
        raise HTTPException(
            status_code=400,
            detail="No id_token in response"
        )
    
    # Verify and decode ID token
    try:
        id_token_claims = id_token.verify_oauth2_token(
            id_token_str,
            google_requests.Request(),
            settings.google_client_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid id_token: {str(e)}"
        )
    
    # Extract user information
    email = id_token_claims.get("email")
    sub = id_token_claims.get("sub")
    
    if not email or not sub:
        raise HTTPException(
            status_code=400,
            detail="Missing email or sub in id_token"
        )
    
    # Get or create user
    user = get_or_create_user(session, email, provider="google")
    
    # Generate JWT token and redirect to custom scheme for mobile app
    token_response = generate_token_response(user)
    token_response["provider"] = "google"  # Add provider to response
    
    # Build redirect URL with token in fragment (# not ? for security)
    callback_url = "nextarget://callback"
    fragment = urlencode(token_response)
    redirect_url = f"{callback_url}#{fragment}"
    
    return RedirectResponse(url=redirect_url, status_code=302)
