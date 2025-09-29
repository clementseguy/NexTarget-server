from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from ..schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserPublic
from ..models.user import User
from ..core.security import hash_password, verify_password, create_access_token
from ..services.database import get_session
from fastapi import Query
from datetime import datetime

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserPublic, status_code=201)
def register(payload: RegisterRequest, session: Session = Depends(get_session)):
    # Check existing by email+provider
    existing = session.exec(
        select(User).where(User.email == payload.email, User.provider == payload.provider)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already exists for this provider")

    hashed_pw = hash_password(payload.password) if payload.provider == "local" else None
    user = User(email=payload.email, provider=payload.provider, hashed_password=hashed_pw)
    session.add(user)
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise HTTPException(status_code=400, detail="Unable to create user")
    session.refresh(user)
    return user

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, session: Session = Depends(get_session)):
    if payload.provider != "local":
        raise HTTPException(status_code=400, detail="Use external provider flow for non-local login")
    user = session.exec(
        select(User).where(User.email == payload.email, User.provider == "local")
    ).first()
    if not user or not user.hashed_password or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(sub=user.id)
    return TokenResponse(access_token=token)


# --- Google OAuth placeholders -------------------------------------------------
@router.get("/google/start")
def google_start(redirect_uri: str = Query(..., description="Client redirect URI")):
    # In real flow: generate state, build Google auth URL
    return {"auth_url": "https://accounts.google.com/o/oauth2/v2/auth?mock=1", "state": "mock_state"}


@router.get("/google/callback")
def google_callback(code: str = "mock_code", state: str = "mock_state", session: Session = Depends(get_session)):
    # In real flow: exchange code -> tokens, verify id_token, extract email, sub
    # Mock user creation / retrieval
    email = f"mock_google_user_{datetime.utcnow().timestamp()}@example.com"
    existing = session.exec(select(User).where(User.email == email, User.provider == "google")).first()
    if not existing:
        user = User(email=email, provider="google", hashed_password=None)
        session.add(user)
        session.commit()
        session.refresh(user)
    else:
        user = existing
    token = create_access_token(sub=user.id)
    return {"access_token": token, "token_type": "bearer", "email": user.email}
