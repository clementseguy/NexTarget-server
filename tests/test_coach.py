import logging
from unittest.mock import AsyncMock, patch

import pytest
from sqlmodel import Session

from app.core.logging import get_logger
from app.core.security import create_access_token
from app.models.user import User
from app.services.database import engine
from app.services.rate_limiter import coach_rate_limiter
from tests.conftest import client


@pytest.fixture(autouse=True, scope="function")
def reset_rate_limiter():
    coach_rate_limiter._hits.clear()
    yield


def _make_user(experience_level=None) -> User:
    with Session(engine) as session:
        user = User(
            email="tireur@example.com",
            provider="google",
            experience_level=experience_level,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


VALID_PAYLOAD = {
    "session": {
        "weapon": "Glock 17",
        "caliber": "9mm",
        "exerciseId": "exercise-1",
        "series": [
            {
                "shot_count": 5,
                "distance": 25,
                "points": 45,
                "group_size_cm": 8.5,
                "comment": "stable",
            },
        ],
        "synthese": "RAS",
    },
    "prompt_variant": "coach_neutre",
}


@pytest.mark.asyncio
async def test_analyze_session_requires_auth():
    async with client() as ac:
        r = await ac.post("/coach/analyze-session", json=VALID_PAYLOAD)
        assert r.status_code == 401


@pytest.mark.asyncio
async def test_analyze_session_success():
    user = _make_user()
    token = create_access_token(sub=user.id)

    with patch(
        "app.api.coach.mistral_client.fetch_analysis",
        new=AsyncMock(return_value="Analyse test."),
    ):
        async with client() as ac:
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
async def test_analyze_session_logs_received_contract_without_free_text(caplog):
    user = _make_user(experience_level="advanced")
    token = create_access_token(sub=user.id)
    coach_logger = get_logger("nextarget.coach")
    previous_level = coach_logger.level
    coach_logger.setLevel(logging.DEBUG)
    coach_logger.addHandler(caplog.handler)
    try:
        with patch(
            "app.api.coach.mistral_client.fetch_analysis",
            new=AsyncMock(return_value="Analyse test."),
        ):
            async with client() as ac:
                response = await ac.post(
                    "/coach/analyze-session",
                    json=VALID_PAYLOAD,
                    headers={"Authorization": f"Bearer {token}"},
                )
    finally:
        coach_logger.removeHandler(caplog.handler)
        coach_logger.setLevel(previous_level)

    assert response.status_code == 200
    record = next(
        item
        for item in caplog.records
        if item.getMessage() == "coach analysis contract"
    )
    assert record.user == {"id": user.id, "experience_level": "advanced"}
    assert record.prompt_variant == "coach_neutre"
    assert record.received_session_fields == [
        "caliber",
        "exerciseId",
        "series",
        "synthese",
        "weapon",
    ]
    assert record.session["exercise_id"] == "exercise-1"
    assert record.session["series_count"] == 1
    assert record.session["series"][0]["has_comment"] is True
    assert "stable" not in str(record.__dict__)
    assert "RAS" not in str(record.__dict__)


@pytest.mark.asyncio
async def test_analyze_session_mistral_timeout_returns_504():
    from app.services.mistral_client import MistralClientError

    user = _make_user()
    token = create_access_token(sub=user.id)

    async def raise_timeout(prompt):
        raise MistralClientError("Le modèle ne répond pas (timeout).", status_code=504)

    with patch("app.api.coach.mistral_client.fetch_analysis", new=raise_timeout):
        async with client() as ac:
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

    async with client() as ac:
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

    with patch(
        "app.api.coach.mistral_client.fetch_analysis", new=AsyncMock(return_value="ok")
    ):
        async with client() as ac:
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


@pytest.mark.asyncio
async def test_analyze_session_accepts_coach_cool_variant():
    """NT-032: the 'coach_cool' persona is a valid prompt variant."""
    user = _make_user()
    token = create_access_token(sub=user.id)

    payload = dict(VALID_PAYLOAD)
    payload["prompt_variant"] = "coach_cool"

    with patch(
        "app.api.coach.mistral_client.fetch_analysis",
        new=AsyncMock(return_value="Analyse cool."),
    ):
        async with client() as ac:
            r = await ac.post(
                "/coach/analyze-session",
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )
    assert r.status_code == 200
    assert r.json()["analysis"] == "Analyse cool."


def test_prompt_builder_variants_produce_distinct_prompts():
    """NT-032: both personas load and assemble distinct templates."""
    from app.schemas.coach import SessionIn, SeriesIn
    from app.services.prompt_builder import build_prompt

    session = SessionIn(
        weapon="Glock 17",
        caliber="9mm",
        exerciseId="exercise-1",
        series=[
            SeriesIn(
                shot_count=5,
                distance=25,
                points=45,
                group_size_cm=8.5,
                comment="stable",
            )
        ],
        synthese="RAS",
    )
    neutral = build_prompt(session, "coach_neutre")
    cool = build_prompt(session, "coach_cool")

    assert neutral != cool
    # Les données de session sont présentes dans les deux variantes.
    for prompt in (neutral, cool):
        assert "Glock 17" in prompt
        assert "Groupement=8.5cm" in prompt


def test_session_contract_accepts_missing_exercise_id():
    """Historical clients can omit the optional exercise identifier."""
    from app.schemas.coach import SessionIn, SeriesIn

    session = SessionIn(
        series=[SeriesIn(shot_count=5, distance=25, points=45, group_size_cm=8.5)]
    )

    properties = SessionIn.schema(by_alias=True)["properties"]
    assert session.exercise_id is None
    assert "exerciseId" in properties
    assert "prescriptionId" not in properties
