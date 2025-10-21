import pytest
from httpx import AsyncClient
from sqlmodel import SQLModel
from app.main import app
from app.services.database import engine

@pytest.fixture(autouse=True, scope="function")
def reset_db():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    yield

@pytest.mark.asyncio
async def test_health_endpoint():
    """Test that health endpoint works"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

@pytest.mark.asyncio
async def test_google_login_endpoint_returns_auth_url():
    """Test that /auth/google/login returns a valid auth URL"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/auth/google/login")
        
        # Should return 500 if not configured, or 200 with auth_url if configured
        if r.status_code == 500:
            # Google OAuth not configured in test environment
            assert "not configured" in r.json()["detail"].lower()
        else:
            assert r.status_code == 200
            data = r.json()
            assert "auth_url" in data
            assert "state" in data
            assert "accounts.google.com" in data["auth_url"]


@pytest.mark.asyncio
async def test_google_start_endpoint_legacy():
    """Test that legacy /auth/google/start still works"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/auth/google/start")
        
        # Should behave exactly like /login
        if r.status_code == 500:
            assert "not configured" in r.json()["detail"].lower()
        else:
            assert r.status_code == 200
            data = r.json()
            assert "auth_url" in data
            assert "state" in data


@pytest.mark.asyncio
async def test_token_exchange_with_invalid_token():
    """Test that token exchange rejects invalid tokens"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post(
            "/auth/token/exchange",
            json={"callback_token": "invalid.token.here"}
        )
        
        assert r.status_code == 401
        assert "Invalid callback token" in r.json()["detail"]


@pytest.mark.asyncio
async def test_token_exchange_with_wrong_token_type():
    """Test that token exchange rejects non-callback tokens"""
    from app.core.security import create_access_token
    
    # Create a regular access token (not a callback token)
    access_token = create_access_token(sub="test-user-id")
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post(
            "/auth/token/exchange",
            json={"callback_token": access_token}
        )
        
        assert r.status_code == 401
        assert "Invalid token type" in r.json()["detail"]


def test_callback_token_creation():
    """Test that callback tokens are created correctly"""
    from app.core.security import create_callback_token, verify_callback_token
    import time
    
    # Create callback token
    token = create_callback_token(
        sub="user-123",
        provider="google",
        email="test@example.com"
    )
    
    # Verify it's valid
    payload = verify_callback_token(token)
    
    assert payload["sub"] == "user-123"
    assert payload["type"] == "callback"
    assert payload["provider"] == "google"
    assert payload["email"] == "test@example.com"
    assert payload["exp"] > time.time()  # Not expired


def test_callback_token_expires_correctly():
    """Test that callback tokens have correct expiration (10 minutes)"""
    from app.core.security import create_callback_token
    from app.core.config import get_settings
    import jwt
    import time
    
    settings = get_settings()
    token = create_callback_token(
        sub="user-123",
        provider="google",
        email="test@example.com"
    )
    
    # Decode without verification to check expiration
    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm]
    )
    
    expected_exp = time.time() + (settings.callback_token_exp_minutes * 60)
    actual_exp = payload["exp"]
    
    # Allow 5 seconds tolerance
    assert abs(actual_exp - expected_exp) < 5


# Note: Full OAuth flow tests require mocking external providers (Google, Facebook)
# These tests should be added in future iterations with proper mocking of:
# - Google token exchange and id_token verification
# - Facebook token exchange and /me API calls
# - State manager lifecycle
