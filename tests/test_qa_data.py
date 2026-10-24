"""Local staging fixtures must be reproducible and isolated from other databases."""

from types import SimpleNamespace

import pytest
from sqlmodel import Session, create_engine, select

from app.models.exercise import CoachCatalogExercise
from scripts import qa_data


def test_reset_and_seed_are_reproducible(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'qa.db'}")
    monkeypatch.setattr(qa_data, "engine", engine)
    monkeypatch.setattr(
        qa_data,
        "get_settings",
        lambda: SimpleNamespace(
            environment="staging",
            database_url="sqlite:////data/nextarget-staging.db",
        ),
    )

    qa_data.reset()
    qa_data.seed()
    with Session(engine) as session:
        exercises = session.exec(select(CoachCatalogExercise)).all()
    assert {exercise.id: exercise.is_active for exercise in exercises} == {
        "qa-catalog-precision-001": True,
        "qa-catalog-inactive-001": False,
    }

    qa_data.reset()
    with Session(engine) as session:
        exercises = session.exec(select(CoachCatalogExercise)).all()
    assert len(exercises) == 2


@pytest.mark.parametrize(
    ("environment", "database_url"),
    [
        ("production", "sqlite:////data/nextarget-staging.db"),
        ("staging", "sqlite:////data/other.db"),
        ("staging", "postgresql://localhost/qa"),
    ],
)
def test_qa_data_rejects_non_staging_database(
    monkeypatch, environment, database_url
):
    monkeypatch.setattr(
        qa_data,
        "get_settings",
        lambda: SimpleNamespace(environment=environment, database_url=database_url),
    )
    with pytest.raises(RuntimeError, match="isolated local staging"):
        qa_data.reset()
