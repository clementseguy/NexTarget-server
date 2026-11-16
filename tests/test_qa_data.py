"""Local staging fixtures must be reproducible and isolated from other databases."""

from types import SimpleNamespace

import pytest
from sqlmodel import Session, create_engine, select

from app.models.exercise import CoachCatalogExercise
from app.services.staging_readiness import is_staging_ready
from scripts import qa_data


def test_reset_and_seed_are_reproducible(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'qa.db'}")
    monkeypatch.setattr(qa_data, "engine", engine)
    monkeypatch.setattr(qa_data, "_database_file", tmp_path / "qa.db")
    monkeypatch.setenv("NEXTARGET_QA_MAINTENANCE", "1")
    monkeypatch.setattr(
        qa_data,
        "get_settings",
        lambda: SimpleNamespace(
            environment="staging",
            database_url="sqlite:////data/nextarget-staging.db",
            source_revision="a" * 40,
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
    assert is_staging_ready(engine, "a" * 40)
    assert not is_staging_ready(engine, "b" * 40)

    qa_data.reset()
    with Session(engine) as session:
        exercises = session.exec(select(CoachCatalogExercise)).all()
    assert len(exercises) == 2
    assert is_staging_ready(engine, "a" * 40)


def test_reset_requires_offline_maintenance(monkeypatch):
    monkeypatch.delenv("NEXTARGET_QA_MAINTENANCE", raising=False)
    monkeypatch.setattr(
        qa_data,
        "get_settings",
        lambda: SimpleNamespace(
            environment="staging",
            database_url="sqlite:////data/nextarget-staging.db",
        ),
    )
    with pytest.raises(RuntimeError, match="offline maintenance"):
        qa_data.reset()


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
