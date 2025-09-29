import pytest
from httpx import AsyncClient
from sqlmodel import SQLModel
from app.main import app
from app.services.database import engine

@pytest.fixture(autouse=True, scope="module")
def create_db():
    # Recreate tables for test isolation (simple approach for SQLite)
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    yield

@pytest.mark.asyncio
async def test_register_and_login():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Register
        r = await ac.post("/auth/register", json={"email": "user@example.com", "password": "Secret123!"})
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["email"] == "user@example.com"

        # Login
        r2 = await ac.post("/auth/login", json={"email": "user@example.com", "password": "Secret123!"})
        assert r2.status_code == 200, r2.text
        token = r2.json()["access_token"]
        assert token

        # /users/me
        r3 = await ac.get("/users/me", headers={"Authorization": f"Bearer {token}"})
        assert r3.status_code == 200, r3.text
        me = r3.json()
        assert me["email"] == "user@example.com"
