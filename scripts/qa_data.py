#!/usr/bin/env python3
"""Reset and seed only the isolated local QA staging SQLite database."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

from sqlmodel import SQLModel, Session

from app.core.config import get_settings
from app.models.exercise import CoachCatalogExercise
from app.services.database import engine


def _require_local_staging() -> None:
    """Reject execution outside the explicitly isolated staging database."""
    settings = get_settings()
    if (
        settings.environment != "staging"
        or settings.database_url != "sqlite:////data/nextarget-staging.db"
    ):
        raise RuntimeError(
            "QA data commands require the isolated local staging SQLite database."
        )


def reset() -> None:
    """Recreate the local staging schema and restore its deterministic fixtures."""
    _require_local_staging()
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    seed()


def seed() -> None:
    """Upsert deterministic, non-production fixtures used by mobile QA."""
    _require_local_staging()
    fixtures = (
        CoachCatalogExercise(
            id="qa-catalog-precision-001",
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
            id="qa-catalog-inactive-001",
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
