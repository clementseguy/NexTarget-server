import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from sqlmodel import SQLModel, Session

from app.main import app
from app.services.database import engine
from app.models.user import User
from app.core.security import create_access_token
from app.services.rate_limiter import coach_rate_limiter


@pytest.fixture(autouse=True, scope="function")
def reset_db():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    coach_rate_limiter._hits.clear()
    yield


def _make_user() -> User:
    with Session(engine) as session:
        user = User(email="tireur@example.com", provider="google")
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


VALID_PAYLOAD = {
    "session": {
        "weapon": "Glock 17",
        "caliber": "9mm",
        "series": [
            {"shot_count": 5, "distance": 25, "points": 45, "group_size_cm": 8.5, "comment": "stable"},
        ],
        "synthese": "RAS",
    },
    "prompt_variant": "coach_neutre",
}


@pytest.mark.asyncio
async def test_analyze_session_requires_auth():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post("/coach/analyze-session", json=VALID_PAYLOAD)
        assert r.status_code == 401


@pytest.mark.asyncio
async def test_analyze_session_success():
    user = _make_user()
    token = create_access_token(sub=user.id)

    with patch("app.api.coach.mistral_client.fetch_analysis", new=AsyncMock(return_value="Analyse test.")):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            r = await ac.post(
                "/coach/analyze-session",
                json=VALID_PAYLOAD,
                headers={"Authorization": f"Bearer {token}"},
            )
    assert r.status_code == 200
    data = r.json()
    assert data["analysis"] == "Analyse test."
    assert "model" in data
    assert "generated_at" in data


@pytest.mark.asyncio
async def test_analyze_session_mistral_timeout_returns_504():
    from app.services.mistral_client import MistralClientError

    user = _make_user()
    token = create_access_token(sub=user.id)

    async def raise_timeout(prompt):
        raise MistralClientError("Le modèle ne répond pas (timeout).", status_code=504)

    with patch("app.api.coach.mistral_client.fetch_analysis", new=raise_timeout):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            r = await ac.post(
                "/coach/analyze-session",
                json=VALID_PAYLOAD,
                headers={"Authorization": f"Bearer {token}"},
            )
    assert r.status_code == 504


@pytest.mark.asyncio
async def test_analyze_session_unknown_prompt_variant_returns_422():
    user = _make_user()
    token = create_access_token(sub=user.id)

    payload = dict(VALID_PAYLOAD)
    payload["prompt_variant"] = "coach_inexistant"

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post(
            "/coach/analyze-session",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_analyze_session_rate_limited_after_threshold():
    user = _make_user()
    token = create_access_token(sub=user.id)

    with patch("app.api.coach.mistral_client.fetch_analysis", new=AsyncMock(return_value="ok")):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            statuses = []
            for _ in range(11):
                r = await ac.post(
                    "/coach/analyze-session",
                    json=VALID_PAYLOAD,
                    headers={"Authorization": f"Bearer {token}"},
                )
                statuses.append(r.status_code)
    assert statuses[-1] == 429
    assert statuses.count(200) == 10
