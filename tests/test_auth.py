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
async def test_register_login_local():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post("/auth/register", json={"email": "user@example.com", "password": "Secret123!", "provider": "local"})
        assert r.status_code == 201
        r2 = await ac.post("/auth/login", json={"email": "user@example.com", "password": "Secret123!", "provider": "local"})
        assert r2.status_code == 200
        token = r2.json()["access_token"]
        me = await ac.get("/users/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200

@pytest.mark.asyncio
async def test_register_non_local_without_password():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post("/auth/register", json={"email": "g1@example.com", "provider": "google"})
        assert r.status_code == 201
        data = r.json()
        assert data["provider"] == "google"
        # login local should fail
        r2 = await ac.post("/auth/login", json={"email": "g1@example.com", "password": "xx", "provider": "local"})
        assert r2.status_code in (400, 401)

@pytest.mark.asyncio
async def test_uniqueness_email_provider():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r1 = await ac.post("/auth/register", json={"email": "dup@example.com", "password": "Secret123!", "provider": "local"})
        assert r1.status_code == 201
        r2 = await ac.post("/auth/register", json={"email": "dup@example.com", "password": "Secret123!", "provider": "local"})
        assert r2.status_code == 400
        # Same email but different provider allowed
        r3 = await ac.post("/auth/register", json={"email": "dup@example.com", "provider": "google"})
        assert r3.status_code == 201
