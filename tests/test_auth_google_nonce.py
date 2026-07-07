"""Tests for Google OIDC nonce verification in the OAuth callback (NT-066).

The Google token exchange and id_token verification are mocked: no real
network call is made. First building block of the mocked-provider test
suite (NT-054).
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlmodel import SQLModel

from app.main import app
from app.services.database import engine
from app.services.oauth_state import get_state_manager


@pytest.fixture(autouse=True, scope="function")
def reset_db():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    yield


@pytest.fixture
def google_configured(monkeypatch):
    """Force a valid Google OAuth configuration on the module-level settings."""
    from app.api import auth_google

    monkeypatch.setattr(auth_google.settings, "google_client_id", "client-id")
    monkeypatch.setattr(auth_google.settings, "google_client_secret", "client-secret")
    monkeypatch.setattr(
        auth_google.settings,
        "google_redirect_uri",
        "http://localhost:8000/auth/google/callback",
    )


def _mock_token_exchange():
    """Mock httpx.AsyncClient so the code exchange returns a fake id_token."""
    response = MagicMock(status_code=200)
    response.json = MagicMock(return_value={"id_token": "fake-id-token"})

    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.post = AsyncMock(return_value=response)

    return patch("app.api.auth_google.httpx.AsyncClient", return_value=client)


def _claims(nonce=None, **overrides):
    claims = {
        "email": "tireur@example.com",
        "sub": "google-sub-123",
        "name": "Tireur Test",
        "picture": "https://example.com/photo.jpg",
    }
    if nonce is not None:
        claims["nonce"] = nonce
    claims.update(overrides)
    return claims


async def _call_callback(state: str, claims: dict):
    with _mock_token_exchange(), patch(
        "app.api.auth_google.id_token.verify_oauth2_token",
        return_value=claims,
    ):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            return await ac.get(
                "/auth/google/callback",
                params={"code": "auth-code", "state": state},
            )


@pytest.mark.asyncio
async def test_callback_accepts_matching_nonce(google_configured):
    state, state_data = get_state_manager().create_state()

    r = await _call_callback(state, _claims(nonce=state_data["nonce"]))

    assert r.status_code == 302
    assert r.headers["location"].startswith("nextarget://callback?token=")


@pytest.mark.asyncio
async def test_callback_rejects_wrong_nonce(google_configured):
    state, _ = get_state_manager().create_state()

    r = await _call_callback(state, _claims(nonce="attacker-nonce"))

    assert r.status_code == 400
    assert r.json()["detail"] == "Invalid nonce"


@pytest.mark.asyncio
async def test_callback_rejects_missing_nonce(google_configured):
    state, _ = get_state_manager().create_state()

    r = await _call_callback(state, _claims(nonce=None))

    assert r.status_code == 400
    assert r.json()["detail"] == "Invalid nonce"


@pytest.mark.asyncio
async def test_callback_rejects_unknown_state(google_configured):
    # State never created server-side: rejected before any nonce logic.
    r = await _call_callback("forged-state", _claims(nonce="whatever"))

    assert r.status_code == 400
    assert "state" in r.json()["detail"].lower()
