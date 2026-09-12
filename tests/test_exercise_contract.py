import json

import pytest
from pydantic import ValidationError
from sqlmodel import SQLModel

from app.models.exercise import (
    ExerciseCategory,
    ExerciseDifficulty,
    ExerciseOrigin,
    ExerciseType,
)
from app.schemas.exercise import ExerciseSchema


EXERCISE_PAYLOAD = {
    "id": "exercise-contract",
    "name": "Contrat",
    "category": "group",
    "type": "stand",
    "difficulty": "beginner",
    "origin": "coach_catalog",
    "description": "Description",
    "durationMinutes": 15,
    "equipment": "Pistolet",
    "createdAt": "2026-09-11T00:00:00.000Z",
    "priority": 3,
    "goalIds": ["goal-1"],
    "consignes": ["Étape 1"],
}


def test_complete_exercise_contract_uses_shared_names_and_values():
    exercise = ExerciseSchema.model_validate(EXERCISE_PAYLOAD)

    assert exercise.id == "exercise-contract"
    assert exercise.category is ExerciseCategory.group
    assert exercise.type is ExerciseType.stand
    assert exercise.difficulty is ExerciseDifficulty.beginner
    assert exercise.origin is ExerciseOrigin.coach_catalog
    assert exercise.duration_minutes == 15
    assert exercise.goal_ids == ["goal-1"]

    serialized = json.loads(exercise.json(by_alias=True))
    assert set(serialized) == set(EXERCISE_PAYLOAD)
    assert serialized["origin"] == "coach_catalog"
    assert serialized["durationMinutes"] == 15
    assert serialized["goalIds"] == ["goal-1"]
    assert "serverId" not in serialized
    assert "version" not in serialized

    schema = ExerciseSchema.schema(by_alias=True)
    assert set(schema["properties"]) == set(EXERCISE_PAYLOAD)
    assert set(schema["required"]) == {
        "id",
        "name",
        "category",
        "type",
        "createdAt",
    }


def test_exercise_enums_match_the_app_contract():
    assert [value.value for value in ExerciseCategory] == [
        "precision",
        "group",
        "speed",
        "technique",
        "mental",
        "physical",
    ]
    assert [value.value for value in ExerciseType] == ["stand", "home"]
    assert [value.value for value in ExerciseDifficulty] == [
        "beginner",
        "advanced",
        "expert",
    ]
    assert [value.value for value in ExerciseOrigin] == [
        "personal",
        "coach_catalog",
    ]


def test_missing_origin_defaults_to_personal():
    payload = {**EXERCISE_PAYLOAD}
    payload.pop("origin")

    exercise = ExerciseSchema.model_validate(payload)

    assert exercise.origin is ExerciseOrigin.personal


@pytest.mark.parametrize("origin", ["server", "coach", 1])
def test_unknown_or_invalid_origin_is_rejected(origin):
    with pytest.raises(ValidationError):
        ExerciseSchema.model_validate({**EXERCISE_PAYLOAD, "origin": origin})


def test_exercise_domain_model_does_not_create_a_database_table():
    assert "exercise" not in SQLModel.metadata.tables
