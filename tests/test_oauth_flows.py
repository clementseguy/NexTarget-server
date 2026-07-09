"""Full OAuth flows with mocked external providers (NT-054).

Google and Facebook HTTP exchanges are entirely mocked: these tests cover
the nominal end-to-end paths (login → callback → token exchange → /users/me)
and the error branches, without any real network call.
"""
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import pytest

from app.services.oauth_state import get_state_manager
from tests.conftest import client, http_response, mock_async_http_client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

GOOGLE_CLAIMS = {
    "email": "tireur@example.com",
    "sub": "google-sub-123",
    "name": "Tireur Test",
    "picture": "https://example.com/photo.jpg",
}


def _google_claims(nonce, **overrides):
    claims = dict(GOOGLE_CLAIMS)
    claims["nonce"] = nonce
    claims.update(overrides)
    return claims


async def _google_callback(state, claims, token_payload=None, token_status=200):
    """Call /auth/google/callback with a mocked code exchange + id_token."""
    payload = {"id_token": "fake-id-token"} if token_payload is None else token_payload
    exchange = mock_async_http_client([http_response(token_status, payload, text="err")])
    with patch("app.api.auth_google.httpx.AsyncClient", return_value=exchange), patch(
        "app.api.auth_google.id_token.verify_oauth2_token",
        return_value=claims,
    ):
        async with client() as ac:
            return await ac.get(
                "/auth/google/callback",
                params={"code": "auth-code", "state": state},
            )


# ---------------------------------------------------------------------------
# Google — flow complet nominal
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_google_full_flow_login_to_users_me(google_configured):
    """login → callback (mocked Google) → token exchange → /users/me."""
    # 1. /login returns an auth_url + state
    async with client() as ac:
        r = await ac.get("/auth/google/login")
    assert r.status_code == 200
    state = r.json()["state"]
    auth_url = r.json()["auth_url"]
    assert "accounts.google.com" in auth_url

    # The nonce sent to Google is bound to the state server-side.
    nonce = parse_qs(urlparse(auth_url).query)["nonce"][0]

    # 2. Google redirects to the callback (exchange mocked)
    r = await _google_callback(state, _google_claims(nonce))
    assert r.status_code == 302
    location = r.headers["location"]
    assert location.startswith("nextarget://callback?token=")
    callback_token = parse_qs(urlparse(location).query)["token"][0]

    # 3. The app exchanges the callback token for an access token
    async with client() as ac:
        r = await ac.post("/auth/token/exchange", json={"callback_token": callback_token})
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == GOOGLE_CLAIMS["email"]
    assert data["provider"] == "google"

    # 4. The access token gives access to the API
    async with client() as ac:
        r = await ac.get(
            "/users/me",
            headers={"Authorization": f"Bearer {data['access_token']}"},
        )
    assert r.status_code == 200
    assert r.json()["email"] == GOOGLE_CLAIMS["email"]
    assert r.json()["display_name"] == GOOGLE_CLAIMS["name"]


# ---------------------------------------------------------------------------
# Google — branches d'erreur
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_google_callback_token_exchange_failure_returns_400(google_configured):
    state, data = get_state_manager().create_state()
    r = await _google_callback(state, _google_claims(data["nonce"]), token_status=500)
    assert r.status_code == 400
    assert "Token exchange failed" in r.json()["detail"]


@pytest.mark.asyncio
async def test_google_callback_missing_id_token_returns_400(google_configured):
    state, data = get_state_manager().create_state()
    r = await _google_callback(state, _google_claims(data["nonce"]), token_payload={})
    assert r.status_code == 400
    assert "No id_token" in r.json()["detail"]


@pytest.mark.asyncio
async def test_google_callback_invalid_id_token_returns_400(google_configured):
    state, _ = get_state_manager().create_state()
    exchange = mock_async_http_client([http_response(200, {"id_token": "bad"})])
    with patch("app.api.auth_google.httpx.AsyncClient", return_value=exchange), patch(
        "app.api.auth_google.id_token.verify_oauth2_token",
        side_effect=ValueError("Invalid signature"),
    ):
        async with client() as ac:
            r = await ac.get(
                "/auth/google/callback",
                params={"code": "auth-code", "state": state},
            )
    assert r.status_code == 400
    assert "Invalid id_token" in r.json()["detail"]


@pytest.mark.asyncio
async def test_google_callback_missing_email_returns_400(google_configured):
    state, data = get_state_manager().create_state()
    claims = _google_claims(data["nonce"])
    del claims["email"]
    r = await _google_callback(state, claims)
    assert r.status_code == 400
    assert "Missing email or sub" in r.json()["detail"]


@pytest.mark.asyncio
async def test_google_login_not_configured_returns_500():
    from app.api import auth_google

    if auth_google.settings.google_client_id:
        pytest.skip("Google configured in this environment")
    async with client() as ac:
        r = await ac.get("/auth/google/login")
    assert r.status_code == 500
    assert "not configured" in r.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Facebook — flow nominal + erreurs
# ---------------------------------------------------------------------------

FB_USERINFO = {
    "id": "fb-123",
    "email": "tireur.fb@example.com",
    "name": "Tireur FB",
    "picture": {"data": {"url": "https://example.com/fb.jpg"}},
}


async def _facebook_callback(state, responses):
    fb_client = mock_async_http_client(responses)
    with patch("app.api.auth_facebook.httpx.AsyncClient", return_value=fb_client):
        async with client() as ac:
            return await ac.get(
                "/auth/facebook/callback",
                params={"code": "fb-code", "state": state},
            )


@pytest.mark.asyncio
async def test_facebook_start_returns_auth_url(facebook_configured):
    async with client() as ac:
        r = await ac.get("/auth/facebook/start")
    assert r.status_code == 200
    assert "facebook.com" in r.json()["auth_url"]
    assert r.json()["state"]


@pytest.mark.asyncio
async def test_facebook_full_callback_creates_user_and_redirects(facebook_configured):
    state, _ = get_state_manager().create_state()
    r = await _facebook_callback(
        state,
        [
            http_response(200, {"access_token": "fb-access"}),
            http_response(200, FB_USERINFO),
        ],
    )
    assert r.status_code == 302
    location = r.headers["location"]
    assert location.startswith("nextarget://callback#")
    assert "access_token=" in location
    assert "provider=facebook" in location


@pytest.mark.asyncio
async def test_facebook_callback_invalid_state_returns_400(facebook_configured):
    r = await _facebook_callback("forged-state", [])
    assert r.status_code == 400
    assert "state" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_facebook_callback_token_exchange_failure_returns_400(facebook_configured):
    state, _ = get_state_manager().create_state()
    r = await _facebook_callback(state, [http_response(500, {}, text="boom")])
    assert r.status_code == 400
    assert "Token exchange failed" in r.json()["detail"]


@pytest.mark.asyncio
async def test_facebook_callback_missing_access_token_returns_400(facebook_configured):
    state, _ = get_state_manager().create_state()
    r = await _facebook_callback(state, [http_response(200, {})])
    assert r.status_code == 400
    assert "No access_token" in r.json()["detail"]


@pytest.mark.asyncio
async def test_facebook_callback_hidden_email_uses_placeholder(facebook_configured):
    """Facebook users can hide their email: a stable placeholder is used."""
    from sqlmodel import Session, select

    from app.models.user import User
    from app.services.database import engine

    state, _ = get_state_manager().create_state()
    userinfo = dict(FB_USERINFO)
    userinfo.pop("email")
    r = await _facebook_callback(
        state,
        [
            http_response(200, {"access_token": "fb-access"}),
            http_response(200, userinfo),
        ],
    )
    assert r.status_code == 302

    with Session(engine) as s:
        user = s.exec(select(User).where(User.provider == "facebook")).first()
    assert user is not None
    assert user.email == "fb_fb-123@example.local"


@pytest.mark.asyncio
async def test_facebook_start_not_configured_returns_500():
    from app.api import auth_facebook

    if auth_facebook.settings.facebook_client_id:
        pytest.skip("Facebook configured in this environment")
    async with client() as ac:
        r = await ac.get("/auth/facebook/start")
    assert r.status_code == 500
    assert "not configured" in r.json()["detail"].lower()
