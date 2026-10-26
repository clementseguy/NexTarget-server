#!/usr/bin/env python3
"""Reset and seed only the isolated local QA staging SQLite database."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path

from sqlalchemy import text
from sqlmodel import SQLModel, Session

from app.core.config import STAGING_DATABASE_URL, get_settings
from app.core.staging_contract import (
    STAGING_ACTIVE_EXERCISE_ID,
    STAGING_INACTIVE_EXERCISE_ID,
    STAGING_SCHEMA_VERSION,
)
from app.models.exercise import CoachCatalogExercise
from app.services.database import engine

_database_file = Path("/data/nextarget-staging.db")


def _require_local_staging() -> None:
    """Reject execution outside the explicitly isolated staging database."""
    settings = get_settings()
    if (
        settings.environment != "staging"
        or settings.database_url != STAGING_DATABASE_URL
    ):
        raise RuntimeError(
            "QA data commands require the isolated local staging SQLite database."
        )


def reset() -> None:
    """Replace the stopped staging database and restore its QA fixtures."""
    _require_local_staging()
    if os.getenv("NEXTARGET_QA_MAINTENANCE") != "1":
        raise RuntimeError("QA reset requires the offline maintenance container.")
    engine.dispose()
    for suffix in ("", "-wal", "-shm"):
        _database_file.with_name(_database_file.name + suffix).unlink(missing_ok=True)
    SQLModel.metadata.create_all(engine)
    seed()
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE qa_staging_state "
                "(revision TEXT NOT NULL, schema_version INTEGER NOT NULL)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO qa_staging_state (revision, schema_version) "
                "VALUES (:revision, :schema_version)"
            ),
            {
                "revision": get_settings().source_revision,
                "schema_version": STAGING_SCHEMA_VERSION,
            },
        )


def seed() -> None:
    """Upsert deterministic, non-production fixtures used by mobile QA."""
    _require_local_staging()
    fixtures = (
        CoachCatalogExercise(
            id=STAGING_ACTIVE_EXERCISE_ID,
            name="QA — Précision contrôlée",
            category="precision",
            type="stand",
            difficulty="beginner",
            description="Fixture locale de recette, jamais destinée au catalogue produit.",
            durationMinutes=15,
            equipment="Cible de recette",
            createdAt=datetime(2026, 10, 12, tzinfo=timezone.utc),
            priority=10,
            goalIds=[],
            consignes=["Appliquer le protocole de recette."],
        ),
        CoachCatalogExercise(
            id=STAGING_INACTIVE_EXERCISE_ID,
            name="QA — Inactif",
            category="technique",
            type="home",
            description="Fixture locale inactive pour les scénarios d'erreur.",
            createdAt=datetime(2026, 10, 12, tzinfo=timezone.utc),
            priority=20,
            goalIds=[],
            consignes=[],
            is_active=False,
        ),
    )
    with Session(engine) as session:
        for fixture in fixtures:
            session.merge(fixture)
        session.commit()


def main() -> int:
    """Run the requested local QA data operation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("reset", "seed"))
    args = parser.parse_args()
    if args.operation == "reset":
        reset()
    else:
        seed()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
