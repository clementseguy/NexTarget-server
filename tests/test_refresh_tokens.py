"""Refresh tokens: issuance, rotation, reuse detection, revocation (NT-048)."""
from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, select

from app.core.security import create_callback_token
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.services.database import engine
from tests.conftest import client


def _make_user() -> User:
    with Session(engine) as session:
        user = User(email="tireur@example.com", provider="google")
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


async def _exchange(user: User) -> dict:
    callback = create_callback_token(sub=user.id, provider="google", email=user.email)
    async with client() as ac:
        r = await ac.post("/auth/token/exchange", json={"callback_token": callback})
    assert r.status_code == 200
    return r.json()


@pytest.mark.asyncio
async def test_exchange_returns_refresh_token():
    user = _make_user()
    data = await _exchange(user)

    assert data["refresh_token"]
    assert data["refresh_expires_in"] == 30 * 24 * 3600
    # Seul le hash est persisté, jamais le token brut.
    with Session(engine) as s:
        record = s.exec(select(RefreshToken)).one()
    assert record.user_id == user.id
    assert record.token_hash != data["refresh_token"]
    assert data["refresh_token"] not in record.token_hash


@pytest.mark.asyncio
async def test_refresh_rotates_token_and_returns_new_pair():
    user = _make_user()
    first = await _exchange(user)

    async with client() as ac:
        r = await ac.post("/auth/token/refresh", json={"refresh_token": first["refresh_token"]})
    assert r.status_code == 200
    second = r.json()

    assert second["access_token"]
    assert second["refresh_token"] != first["refresh_token"]
    assert second["user_id"] == user.id

    # Le nouveau refresh token fonctionne à son tour.
    async with client() as ac:
        r = await ac.post("/auth/token/refresh", json={"refresh_token": second["refresh_token"]})
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_refreshed_access_token_gives_api_access():
    user = _make_user()
    first = await _exchange(user)

    async with client() as ac:
        r = await ac.post("/auth/token/refresh", json={"refresh_token": first["refresh_token"]})
        access = r.json()["access_token"]
        r = await ac.get("/users/me", headers={"Authorization": f"Bearer {access}"})
    assert r.status_code == 200
    assert r.json()["email"] == user.email


@pytest.mark.asyncio
async def test_reuse_of_rotated_token_revokes_family():
    """Rejouer un refresh token déjà consommé révoque toute la famille."""
    user = _make_user()
    first = await _exchange(user)

    async with client() as ac:
        r = await ac.post("/auth/token/refresh", json={"refresh_token": first["refresh_token"]})
        second = r.json()

        # Rejeu de l'ancien token → 401 + révocation de la famille.
        r = await ac.post("/auth/token/refresh", json={"refresh_token": first["refresh_token"]})
        assert r.status_code == 401
        assert "reuse" in r.json()["detail"].lower()

        # Le token le plus récent de la famille est mort lui aussi.
        r = await ac.post("/auth/token/refresh", json={"refresh_token": second["refresh_token"]})
        assert r.status_code == 401


@pytest.mark.asyncio
async def test_expired_refresh_token_returns_401():
    user = _make_user()
    data = await _exchange(user)

    with Session(engine) as s:
        record = s.exec(select(RefreshToken)).one()
        record.expires_at = datetime.utcnow() - timedelta(seconds=1)
        s.add(record)
        s.commit()

    async with client() as ac:
        r = await ac.post("/auth/token/refresh", json={"refresh_token": data["refresh_token"]})
    assert r.status_code == 401
    assert "expired" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_unknown_refresh_token_returns_401():
    async with client() as ac:
        r = await ac.post("/auth/token/refresh", json={"refresh_token": "garbage"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_revoke_then_refresh_returns_401():
    user = _make_user()
    data = await _exchange(user)

    async with client() as ac:
        r = await ac.post("/auth/token/revoke", json={"refresh_token": data["refresh_token"]})
        assert r.status_code == 204

        r = await ac.post("/auth/token/refresh", json={"refresh_token": data["refresh_token"]})
        assert r.status_code == 401


@pytest.mark.asyncio
async def test_revoke_is_idempotent_and_oracle_free():
    async with client() as ac:
        r = await ac.post("/auth/token/revoke", json={"refresh_token": "unknown-token"})
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_exchange_contract_unchanged_for_existing_clients():
    """NT-048 est additif : les champs historiques d'exchange sont intacts."""
    user = _make_user()
    data = await _exchange(user)

    for field in ("access_token", "token_type", "expires_in", "email", "provider", "user_id"):
        assert field in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 3600
