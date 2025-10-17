from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select

from ..schemas.auth import TokenResponse, UserPublic
from ..models.user import User
from ..core.security import create_access_token
from ..services.database import get_session
from datetime import datetime, timedelta
import secrets
import time
import httpx
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from ..core.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])

settings = get_settings()

# In-memory ephemeral stores (v0.1 only). Replace with Redis in production.
_oauth_states: dict[str, dict] = {}
STATE_TTL_SECONDS = 600

def _prune_states():
    now = time.time()
    expired = [k for k, v in _oauth_states.items() if v["exp"] < now]
    for k in expired:
        _oauth_states.pop(k, None)


# --- Google OAuth real flow ----------------------------------------------------
GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_SCOPES = ["openid", "email", "profile"]

# Facebook
FACEBOOK_AUTH_ENDPOINT = "https://www.facebook.com/v18.0/dialog/oauth"
FACEBOOK_TOKEN_ENDPOINT = "https://graph.facebook.com/v18.0/oauth/access_token"
FACEBOOK_USERINFO_ENDPOINT = "https://graph.facebook.com/me"
FACEBOOK_SCOPES = ["email"]

def _assert_google_config():
    if not (settings.google_client_id and settings.google_client_secret and settings.google_redirect_uri):
        raise HTTPException(status_code=500, detail="Google OAuth not configured")

def _assert_facebook_config():
    if not (settings.facebook_client_id and settings.facebook_client_secret and settings.facebook_redirect_uri):
        raise HTTPException(status_code=500, detail="Facebook OAuth not configured")

@router.get("/google/start")
def google_start(session_nonce: str = Query(None, description="Opaque value from client to bind session")):
    _assert_google_config()
    _prune_states()
    state = secrets.token_urlsafe(24)
    nonce = secrets.token_urlsafe(24)
    _oauth_states[state] = {"nonce": nonce, "created": time.time(), "exp": time.time() + STATE_TTL_SECONDS, "client_nonce": session_nonce}
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": " ".join(GOOGLE_SCOPES),
        "state": state,
        "nonce": nonce,
        "access_type": "offline",
        "prompt": "consent",
    }
    # Build URL manually
    from urllib.parse import urlencode
    auth_url = f"{GOOGLE_AUTH_ENDPOINT}?{urlencode(params)}"
    return {"auth_url": auth_url, "state": state}

@router.get("/google/callback")
async def google_callback(code: str, state: str, session: Session = Depends(get_session)):
    _assert_google_config()
    stored = _oauth_states.get(state)
    if not stored:
        raise HTTPException(status_code=400, detail="Invalid or expired state")
    _oauth_states.pop(state, None)  # one-time use

    # Exchange code -> tokens
    data = {
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": settings.google_redirect_uri,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        token_resp = await client.post(GOOGLE_TOKEN_ENDPOINT, data=data)
    if token_resp.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {token_resp.text}")
    token_payload = token_resp.json()
    id_tok = token_payload.get("id_token")
    if not id_tok:
        raise HTTPException(status_code=400, detail="No id_token in response")

    try:
        info = id_token.verify_oauth2_token(id_tok, google_requests.Request(), settings.google_client_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid id_token: {e}")

    email = info.get("email")
    sub = info.get("sub")
    if not email or not sub:
        raise HTTPException(status_code=400, detail="Missing email or sub in id_token")

    # Upsert user
    user = session.exec(select(User).where(User.email == email, User.provider == "google")).first()
    if not user:
        user = User(email=email, provider="google")
        session.add(user)
        try:
            session.commit()
        except Exception:
            session.rollback()
            raise HTTPException(status_code=500, detail="Failed to create user")
        session.refresh(user)

    jwt_token = create_access_token(sub=user.id, expires_delta=timedelta(minutes=settings.access_token_exp_minutes))
    return {"access_token": jwt_token, "token_type": "bearer", "email": user.email, "provider": user.provider}

# --- Facebook OAuth flow -------------------------------------------------------
@router.get("/facebook/start")
def facebook_start(session_nonce: str = Query(None, description="Opaque value from client to bind session")):
    _assert_facebook_config()
    _prune_states()
    state = secrets.token_urlsafe(24)
    _oauth_states[state] = {"created": time.time(), "exp": time.time() + STATE_TTL_SECONDS, "client_nonce": session_nonce}
    from urllib.parse import urlencode
    params = {
        "client_id": settings.facebook_client_id,
        "redirect_uri": settings.facebook_redirect_uri,
        "state": state,
        "response_type": "code",
        "scope": ",".join(FACEBOOK_SCOPES),
    }
    auth_url = f"{FACEBOOK_AUTH_ENDPOINT}?{urlencode(params)}"
    return {"auth_url": auth_url, "state": state}

@router.get("/facebook/callback")
async def facebook_callback(code: str, state: str, session: Session = Depends(get_session)):
    _assert_facebook_config()
    stored = _oauth_states.get(state)
    if not stored:
        raise HTTPException(status_code=400, detail="Invalid or expired state")
    _oauth_states.pop(state, None)

    params = {
        "client_id": settings.facebook_client_id,
        "redirect_uri": settings.facebook_redirect_uri,
        "client_secret": settings.facebook_client_secret,
        "code": code,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        token_resp = await client.get(FACEBOOK_TOKEN_ENDPOINT, params=params)
    if token_resp.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Facebook token exchange failed: {token_resp.text}")
    token_payload = token_resp.json()
    access_token_fb = token_payload.get("access_token")
    if not access_token_fb:
        raise HTTPException(status_code=400, detail="No access_token returned by Facebook")

    # Fetch user info
    user_params = {"fields": "id,email", "access_token": access_token_fb}
    async with httpx.AsyncClient(timeout=15) as client:
        user_resp = await client.get(FACEBOOK_USERINFO_ENDPOINT, params=user_params)
    if user_resp.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Failed to fetch Facebook user: {user_resp.text}")
    info = user_resp.json()
    fb_id = info.get("id")
    email = info.get("email") or f"fb_{fb_id}@example.local"  # fallback if email missing (user can hide email)
    if not fb_id:
        raise HTTPException(status_code=400, detail="Missing Facebook user id")

    user = session.exec(select(User).where(User.email == email, User.provider == "facebook")).first()
    if not user:
        user = User(email=email, provider="facebook")
        session.add(user)
        try:
            session.commit()
        except Exception:
            session.rollback()
            raise HTTPException(status_code=500, detail="Failed to create user")
        session.refresh(user)

    jwt_token = create_access_token(sub=user.id, expires_delta=timedelta(minutes=settings.access_token_exp_minutes))
    return {"access_token": jwt_token, "token_type": "bearer", "email": user.email, "provider": user.provider}
