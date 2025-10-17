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

# Note: OAuth flow tests require mocking external providers (Google, Facebook)
# These tests should be added in future iterations with proper mocking of:
# - Google token exchange and id_token verification
# - Facebook token exchange and /me API calls
