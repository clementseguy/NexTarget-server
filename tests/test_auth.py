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


# ---------------------------------------------------------------------------
# Helper: create a test user in DB + access token
# ---------------------------------------------------------------------------

def _create_test_user(session, **overrides):
    """Create a User in the test DB and return (user, access_token)."""
    from app.models.user import User
    from app.core.security import create_access_token

    defaults = dict(
        email="test@example.com",
        provider="google",
        display_name="Test User",
        avatar_url="https://lh3.googleusercontent.com/photo.jpg",
    )
    defaults.update(overrides)

    user = User(**defaults)
    session.add(user)
    session.commit()
    session.refresh(user)

    token = create_access_token(sub=user.id)
    return user, token


def _get_test_session():
    from app.services.database import get_session
    return next(get_session())


# ---------------------------------------------------------------------------
# GET /users/me — extended profile
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_me_returns_profile_fields():
    """Test that /users/me returns extended profile fields"""
    session = _get_test_session()
    user, token = _create_test_user(
        session,
        display_name="Alice",
        avatar_url="https://example.com/photo.jpg",
        experience_level="beginner",
    )

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get(
            "/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert r.status_code == 200
    data = r.json()
    assert data["display_name"] == "Alice"
    assert data["avatar_url"] == "https://example.com/photo.jpg"
    assert data["experience_level"] == "beginner"
    assert "created_at" in data
    session.close()


@pytest.mark.asyncio
async def test_get_me_with_null_profile_fields():
    """Test that /users/me works when profile fields are null"""
    session = _get_test_session()
    user, token = _create_test_user(
        session,
        display_name=None,
        avatar_url=None,
        experience_level=None,
    )

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get(
            "/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert r.status_code == 200
    data = r.json()
    assert data["display_name"] is None
    assert data["avatar_url"] is None
    assert data["experience_level"] is None
    session.close()


# ---------------------------------------------------------------------------
# PATCH /users/me/profile — update display_name
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_patch_profile_update_display_name():
    """Test updating display_name via PATCH"""
    session = _get_test_session()
    user, token = _create_test_user(session)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.patch(
            "/users/me/profile",
            headers={"Authorization": f"Bearer {token}"},
            json={"display_name": "New Name"},
        )

    assert r.status_code == 200
    data = r.json()
    assert data["display_name"] == "New Name"
    session.close()


@pytest.mark.asyncio
async def test_patch_profile_display_name_sets_custom_flag():
    """Test that setting display_name marks display_name_custom = True"""
    session = _get_test_session()
    user, token = _create_test_user(session)
    assert user.display_name_custom is False

    async with AsyncClient(app=app, base_url="http://test") as ac:
        await ac.patch(
            "/users/me/profile",
            headers={"Authorization": f"Bearer {token}"},
            json={"display_name": "Custom Name"},
        )

    session.refresh(user)
    assert user.display_name_custom is True
    assert user.display_name == "Custom Name"
    session.close()


@pytest.mark.asyncio
async def test_patch_profile_display_name_null_resets_custom_flag():
    """Test that setting display_name to null resets custom flag"""
    session = _get_test_session()
    user, token = _create_test_user(session)
    user.display_name_custom = True
    session.add(user)
    session.commit()

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.patch(
            "/users/me/profile",
            headers={"Authorization": f"Bearer {token}"},
            json={"display_name": None},
        )

    assert r.status_code == 200
    session.refresh(user)
    assert user.display_name_custom is False
    session.close()


# ---------------------------------------------------------------------------
# PATCH /users/me/profile — update experience_level
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_patch_profile_update_experience_level():
    """Test updating experience_level via PATCH"""
    session = _get_test_session()
    user, token = _create_test_user(session)

    for level in ("beginner", "advanced", "expert"):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            r = await ac.patch(
                "/users/me/profile",
                headers={"Authorization": f"Bearer {token}"},
                json={"experience_level": level},
            )
        assert r.status_code == 200
        assert r.json()["experience_level"] == level

    session.close()


@pytest.mark.asyncio
async def test_patch_profile_invalid_experience_level():
    """Test that invalid experience_level is rejected"""
    session = _get_test_session()
    user, token = _create_test_user(session)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.patch(
            "/users/me/profile",
            headers={"Authorization": f"Bearer {token}"},
            json={"experience_level": "grandmaster"},
        )

    assert r.status_code == 422  # Validation error
    session.close()


@pytest.mark.asyncio
async def test_patch_profile_empty_body_no_change():
    """Test that an empty PATCH body returns user unchanged"""
    session = _get_test_session()
    user, token = _create_test_user(
        session, display_name="Original", experience_level="beginner"
    )

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.patch(
            "/users/me/profile",
            headers={"Authorization": f"Bearer {token}"},
            json={},
        )

    assert r.status_code == 200
    data = r.json()
    assert data["display_name"] == "Original"
    assert data["experience_level"] == "beginner"
    session.close()


@pytest.mark.asyncio
async def test_patch_profile_display_name_too_long():
    """Test that display_name over 100 chars is rejected"""
    session = _get_test_session()
    user, token = _create_test_user(session)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.patch(
            "/users/me/profile",
            headers={"Authorization": f"Bearer {token}"},
            json={"display_name": "A" * 101},
        )

    assert r.status_code == 422
    session.close()


@pytest.mark.asyncio
async def test_patch_profile_requires_auth():
    """Test that PATCH /users/me/profile requires authentication"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.patch(
            "/users/me/profile",
            json={"display_name": "Hacker"},
        )

    assert r.status_code == 401


# ---------------------------------------------------------------------------
# get_or_create_user — profile refresh logic
# ---------------------------------------------------------------------------

def test_get_or_create_user_sets_profile_on_create():
    """Test that get_or_create_user initializes profile fields"""
    from app.api.oauth_utils import get_or_create_user

    session = _get_test_session()
    user = get_or_create_user(
        session,
        email="new@example.com",
        provider="google",
        display_name="New User",
        avatar_url="https://example.com/avatar.jpg",
    )

    assert user.display_name == "New User"
    assert user.avatar_url == "https://example.com/avatar.jpg"
    assert user.display_name_custom is False
    session.close()


def test_get_or_create_user_refreshes_idp_data_on_login():
    """Test that IdP data is refreshed on existing user login"""
    from app.api.oauth_utils import get_or_create_user

    session = _get_test_session()

    # First login
    user = get_or_create_user(
        session,
        email="refresh@example.com",
        provider="google",
        display_name="Old Name",
        avatar_url="https://example.com/old.jpg",
    )
    user_id = user.id

    # Second login with updated IdP data
    user = get_or_create_user(
        session,
        email="refresh@example.com",
        provider="google",
        display_name="New Name",
        avatar_url="https://example.com/new.jpg",
    )

    assert user.id == user_id
    assert user.display_name == "New Name"
    assert user.avatar_url == "https://example.com/new.jpg"
    session.close()


def test_get_or_create_user_preserves_custom_display_name():
    """Test that custom display_name is NOT overwritten by IdP on login"""
    from app.api.oauth_utils import get_or_create_user

    session = _get_test_session()

    # First login
    user = get_or_create_user(
        session,
        email="custom@example.com",
        provider="google",
        display_name="IdP Name",
        avatar_url="https://example.com/photo.jpg",
    )

    # User customizes their name
    user.display_name = "My Custom Name"
    user.display_name_custom = True
    session.add(user)
    session.commit()

    # Second login — should NOT overwrite custom name, but SHOULD update avatar
    user = get_or_create_user(
        session,
        email="custom@example.com",
        provider="google",
        display_name="Updated IdP Name",
        avatar_url="https://example.com/new_photo.jpg",
    )

    assert user.display_name == "My Custom Name"  # Preserved
    assert user.avatar_url == "https://example.com/new_photo.jpg"  # Updated
    session.close()
