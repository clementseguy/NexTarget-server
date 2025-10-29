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
from ..core.security import create_callback_token
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


@router.get("/login")
def google_auth_login(
    session_nonce: str = Query(
        None,
        description="Opaque value from client to bind session"
    ),
    mode: str = Query(
        "json",
        description="Response mode: 'json' (default, returns auth_url) or 'redirect' (302 redirect)"
    )
):
    """
    Initiate Google OAuth 2.0 authorization flow.
    
    Supports two modes:
    - mode=json (default): Returns JSON with auth_url - for native mobile apps (RFC 8252)
    - mode=redirect: HTTP 302 redirect to Google - for web applications
    
    Mobile flow (mode=json):
    1. App calls this endpoint to get auth_url
    2. App opens auth_url in WebView or browser
    3. User authenticates with Google
    4. Google redirects to /callback with code
    5. Backend exchanges code for tokens
    6. Backend redirects to nextarget://callback?token=JWT
    7. App intercepts custom scheme and extracts JWT
    
    Web flow (mode=redirect):
    1. Browser navigates to this endpoint
    2. Server redirects (302) to Google OAuth
    3. User authenticates
    4. Google redirects to /callback
    
    Args:
        session_nonce: Optional client nonce for session binding
        mode: Response mode - 'json' (default) or 'redirect'
        
    Returns:
        - If mode=json: Dictionary with auth_url and state
        - If mode=redirect: RedirectResponse to Google OAuth
        
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
    
    # Mode redirect: HTTP 302 pour applications web
    if mode == "redirect":
        return RedirectResponse(url=auth_url, status_code=302)
    
    # Mode json (default): Retourne l'URL pour applications natives (RFC 8252)
    return {
        "auth_url": auth_url,
        "state": state,
    }


# Keep legacy /start endpoint for backward compatibility
@router.get("/start")
def google_auth_start(
    session_nonce: str = Query(
        None,
        description="Opaque value from client to bind session"
    )
) -> dict:
    """
    Legacy endpoint - use /login instead.
    Maintained for backward compatibility.
    """
    return google_auth_login(session_nonce=session_nonce)


@router.get("/callback")
async def google_auth_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="State token for CSRF protection"),
    session: Session = Depends(get_session),
) -> RedirectResponse:
    """
    Handle Google OAuth callback and redirect to mobile app.
    
    Flow:
    1. Verify state token (CSRF protection)
    2. Exchange authorization code for Google tokens
    3. Verify ID token signature
    4. Get or create user in database
    5. Generate short-lived JWT (10 min)
    6. Redirect to nextarget://callback?token=JWT
    
    Args:
        code: Authorization code from Google
        state: State token for CSRF protection
        session: Database session
        
    Returns:
        RedirectResponse to nextarget://callback?token=JWT
        
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
    
    # Generate short-lived callback token (10 minutes)
    callback_token = create_callback_token(
        sub=user.id,
        provider="google",
        email=user.email
    )
    
    # Redirect to mobile app custom scheme with token as query parameter
    redirect_url = f"nextarget://callback?token={callback_token}"
    
    return RedirectResponse(url=redirect_url, status_code=302)
