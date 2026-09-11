from datetime import datetime, timezone

import pytest
from sqlmodel import Session

from app.main import app
from app.models.exercise import CoachCatalogExercise, ExerciseOrigin
from app.services.database import engine
from tests.conftest import client


def _catalog_exercise(
    exercise_id: str = "coach-fixture",
    *,
    is_active: bool = True,
) -> CoachCatalogExercise:
    return CoachCatalogExercise(
        id=exercise_id,
        name="Fixture Coach",
        category="technique",
        type="stand",
        difficulty="beginner",
        origin="coach_catalog",
        description="Contenu technique de test",
        durationMinutes=15,
        equipment="Matériel de test",
        createdAt=datetime(2026, 9, 11, tzinfo=timezone.utc),
        priority=10,
        goalIds=[],
        consignes=["Consigne de test"],
        is_active=is_active,
    )


def test_catalog_persists_only_coach_exercises_and_defaults_to_active():
    exercise = _catalog_exercise()
    assert exercise.origin is ExerciseOrigin.coach_catalog
    assert exercise.is_active is True

    with Session(engine) as session:
        session.add(exercise)
        session.commit()
        session.refresh(exercise)

    assert exercise.id == "coach-fixture"

    with pytest.raises(ValueError, match="coach_catalog"):
        CoachCatalogExercise(
            id="personal",
            name="Personnel",
            category="precision",
            type="stand",
            origin="personal",
            createdAt=datetime(2026, 9, 11, tzinfo=timezone.utc),
        )


async def test_get_active_catalog_exercise_by_id():
    with Session(engine) as session:
        session.add(_catalog_exercise())
        session.commit()

    async with client() as ac:
        response = await ac.get("/exercises/coach-fixture")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == "coach-fixture"
    assert payload["origin"] == "coach_catalog"
    assert "is_active" not in payload
    assert "isActive" not in payload


@pytest.mark.parametrize("exercise_id", ["missing", "inactive"])
async def test_missing_or_inactive_catalog_exercise_is_not_exposed(exercise_id):
    with Session(engine) as session:
        session.add(_catalog_exercise("inactive", is_active=False))
        session.commit()

    async with client() as ac:
        response = await ac.get(f"/exercises/{exercise_id}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Exercise not found"}


async def test_catalog_has_no_client_list_or_mutation_endpoint():
    async with client() as ac:
        assert (await ac.get("/exercises")).status_code == 404
        assert (await ac.post("/exercises", json={})).status_code == 404
        assert (await ac.put("/exercises/coach-fixture", json={})).status_code == 405
        assert (await ac.delete("/exercises/coach-fixture")).status_code == 405

    paths = app.openapi()["paths"]
    assert set(paths["/exercises/{exercise_id}"]) == {"get"}
    assert "/exercises" not in paths
