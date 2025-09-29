import pytest
from httpx import AsyncClient
from sqlmodel import SQLModel, select, Session

from app.main import app
from app.services.database import engine, get_session
from app.models.ai_interaction import AIInteraction

# Patch mistral_completion by monkeypatch
@pytest.fixture(autouse=True, scope="function")
def reset_db():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    yield

@pytest.mark.asyncio
async def test_ai_completion_and_history(monkeypatch):
    async def fake_mistral(prompt: str, user_id: str):
        return "Réponse synthétique.", "mistral-test"
    # Patch where used (api.ai imports mistral_completion directly)
    import app.api.ai as ai_module
    monkeypatch.setattr(ai_module, "mistral_completion", fake_mistral)
    # Ensure API key check not blocking
    from app.core import config as cfg
    monkeypatch.setattr(cfg.get_settings(), "mistral_api_key", "test-key", raising=False)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        await ac.post("/auth/register", json={"email": "user@example.com", "password": "Secret123!", "provider": "local"})
        token = (await ac.post("/auth/login", json={"email": "user@example.com", "password": "Secret123!", "provider": "local"})).json()["access_token"]
        r = await ac.post("/ai/completions", json={"prompt": "Donne un conseil."}, headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()
        assert "completion" in data

    # Verify history using direct Session
    with Session(engine) as session:
        interactions = session.exec(select(AIInteraction)).all()
        assert len(interactions) == 2  # user + assistant

@pytest.mark.asyncio
async def test_coach_advice_parsing(monkeypatch):
    mock_answer = """1. Faire un plan.
2. Mesurer les progrès.
3. Ajuster chaque semaine.
"""
    async def fake_mistral(prompt: str, user_id: str):
        return mock_answer, "mistral-test"
    import app.services.coach as coach_service
    monkeypatch.setattr(coach_service, "mistral_completion", fake_mistral)
    from app.core import config as cfg
    monkeypatch.setattr(cfg.get_settings(), "mistral_api_key", "test-key", raising=False)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        await ac.post("/auth/register", json={"email": "coach@example.com", "password": "Secret123!", "provider": "local"})
        token = (await ac.post("/auth/login", json={"email": "coach@example.com", "password": "Secret123!", "provider": "local"})).json()["access_token"]
        r = await ac.post("/coach/advice", json={"goal": "Améliorer productivité"}, headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, r.text
        data = r.json()
        assert len(data["advices"]) == 3
        assert {a['text'] for a in data['advices']} == {"Faire un plan.", "Mesurer les progrès.", "Ajuster chaque semaine."}
