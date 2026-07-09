"""Shared test fixtures and helpers (NT-054).

- `client()`: AsyncClient wired to the app via ASGITransport (no deprecated
  `app=` shortcut, no network).
- `reset_db`: fresh schema between tests (autouse).
- `google_configured` / `facebook_configured`: force provider config on the
  module-level settings objects.
- Google/Facebook HTTP exchanges are mocked in tests; nothing ever calls
  the real providers.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlmodel import SQLModel

from app.main import app
from app.services.database import engine


def client() -> AsyncClient:
    """AsyncClient bound to the FastAPI app (in-process, no network).

    base_url en https pour éviter un signal « HTTP insecure » : le scheme
    est purement cosmétique ici, le transport ASGI ne touche pas le réseau.
    """
    return AsyncClient(transport=ASGITransport(app=app), base_url="https://test")


@pytest.fixture(autouse=True, scope="function")
def reset_db():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    yield


@pytest.fixture
def google_configured(monkeypatch):
    """Force a valid Google OAuth configuration."""
    from app.api import auth_google

    monkeypatch.setattr(auth_google.settings, "google_client_id", "client-id")
    monkeypatch.setattr(auth_google.settings, "google_client_secret", "client-secret")
    monkeypatch.setattr(
        auth_google.settings,
        "google_redirect_uri",
        "http://localhost:8000/auth/google/callback",
    )


@pytest.fixture
def facebook_configured(monkeypatch):
    """Force a valid Facebook OAuth configuration."""
    from app.api import auth_facebook

    monkeypatch.setattr(auth_facebook.settings, "facebook_client_id", "fb-client-id")
    monkeypatch.setattr(auth_facebook.settings, "facebook_client_secret", "fb-client-secret")
    monkeypatch.setattr(
        auth_facebook.settings,
        "facebook_redirect_uri",
        "http://localhost:8000/auth/facebook/callback",
    )


def mock_async_http_client(responses):
    """Build a mocked `httpx.AsyncClient` context manager.

    Args:
        responses: list of MagicMock responses returned in order by
            successive `get`/`post` calls (shared queue).

    Returns:
        A MagicMock suitable for `patch("...httpx.AsyncClient", return_value=...)`.
    """
    queue = list(responses)

    def _next_response(*args, **kwargs):
        # side_effect synchrone : AsyncMock enveloppe la valeur de retour.
        return queue.pop(0)

    mock = MagicMock()
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=False)
    mock.post = AsyncMock(side_effect=_next_response)
    mock.get = AsyncMock(side_effect=_next_response)
    return mock


def http_response(status_code=200, json_body=None, text=""):
    """Small helper to build a mocked httpx response."""
    resp = MagicMock(status_code=status_code, text=text)
    resp.json = MagicMock(return_value=json_body or {})
    return resp
