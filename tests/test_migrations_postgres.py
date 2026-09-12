"""Alembic migration + CRUD smoke test against a real PostgreSQL database (NT-071).

Skipped unless NEXTARGET_TEST_POSTGRES_URL points at a disposable PostgreSQL
database. Never point this at a shared/production database: the fixture
applies and then fully rolls back the schema (`alembic downgrade base`).

Local run example:
    createdb nextarget_test
    NEXTARGET_TEST_POSTGRES_URL=postgresql://localhost/nextarget_test \
        pytest tests/test_migrations_postgres.py -v
"""

import os
from datetime import datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, create_engine, select

from app.core.config import get_settings
from app.models.coach import CoachSession, CoachSessionAnalysis
from app.models.refresh_token import RefreshToken
from app.models.exercise import CoachCatalogExercise
from app.models.user import User
from app.services.database import _normalize_database_url

TEST_POSTGRES_URL = os.environ.get("NEXTARGET_TEST_POSTGRES_URL")

pytestmark = pytest.mark.skipif(
    not TEST_POSTGRES_URL,
    reason="NEXTARGET_TEST_POSTGRES_URL not set: PostgreSQL migration test skipped",
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def _alembic_config() -> Config:
    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(REPO_ROOT / "alembic"))
    return cfg


@pytest.fixture
def postgres_schema(monkeypatch):
    """Apply the Alembic schema against the disposable test database, then roll it back."""
    settings = get_settings()
    monkeypatch.setattr(settings, "database_migration_url", TEST_POSTGRES_URL)
    cfg = _alembic_config()
    command.upgrade(cfg, "head")
    try:
        yield
    finally:
        command.downgrade(cfg, "base")


def test_alembic_upgrade_creates_expected_tables(postgres_schema):
    engine = create_engine(_normalize_database_url(TEST_POSTGRES_URL))
    with engine.connect() as conn:
        tables = set(inspect(conn).get_table_names())
    assert {
        "user",
        "refreshtoken",
        "coach_catalog_exercise",
        "coach_session",
        "coach_session_analysis",
    }.issubset(tables)


def test_user_and_refresh_token_crud_against_postgres(postgres_schema):
    engine = create_engine(_normalize_database_url(TEST_POSTGRES_URL))
    with Session(engine) as session:
        user = User(email="pilot@example.com", provider="google")
        session.add(user)
        session.commit()
        session.refresh(user)

        token = RefreshToken(
            user_id=user.id,
            token_hash="hash-value",
            family_id="family-1",
            expires_at=user.created_at,
        )
        session.add(token)
        session.commit()

        fetched = session.exec(
            select(User).where(User.email == "pilot@example.com")
        ).one()
        assert fetched.id == user.id


def test_duplicate_email_provider_is_rejected_by_unique_constraint(postgres_schema):
    engine = create_engine(_normalize_database_url(TEST_POSTGRES_URL))
    with Session(engine) as session:
        session.add(User(email="dup@example.com", provider="google"))
        session.commit()

        session.add(User(email="dup@example.com", provider="google"))
        with pytest.raises(IntegrityError):
            session.commit()


def test_coach_catalog_crud_against_postgres(postgres_schema):
    engine = create_engine(_normalize_database_url(TEST_POSTGRES_URL))
    with Session(engine) as session:
        exercise = CoachCatalogExercise(
            id="coach-postgres-fixture",
            name="Fixture Coach",
            category="technique",
            type="stand",
            origin="coach_catalog",
            createdAt=datetime(2026, 9, 11),
        )
        session.add(exercise)
        session.commit()
        session.refresh(exercise)

        assert exercise.is_active is True
        exercise.is_active = False
        session.add(exercise)
        session.commit()


def test_coach_session_and_analysis_crud_against_postgres(postgres_schema):
    engine = create_engine(_normalize_database_url(TEST_POSTGRES_URL))
    with Session(engine) as session:
        coach_session = CoachSession(
            user_id="user-1",
            client_session_id="123e4567-e89b-42d3-a456-426614174000",
            content_hash="hash",
            snapshot={"series": []},
        )
        session.add(coach_session)
        session.commit()
        session.refresh(coach_session)

        analysis = CoachSessionAnalysis(
            coach_session_id=coach_session.id,
            content_hash="hash",
            prompt_variant="coach_neutre",
            result={"debrief": "test"},
            model="test-model",
        )
        session.add(analysis)
        session.commit()

        assert session.exec(select(CoachSessionAnalysis)).one().result == {
            "debrief": "test"
        }
