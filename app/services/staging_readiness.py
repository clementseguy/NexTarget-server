"""Readiness proof for the disposable local staging database."""

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.core.staging_contract import (
    STAGING_ACTIVE_EXERCISE_ID,
    STAGING_INACTIVE_EXERCISE_ID,
    STAGING_SCHEMA_VERSION,
)


def is_staging_ready(engine: Engine, revision: str) -> bool:
    """Check that the current image owns the schema and QA fixtures."""
    try:
        with engine.connect() as connection:
            state = connection.execute(
                text("SELECT revision, schema_version FROM qa_staging_state")
            ).one_or_none()
            if state is None or tuple(state) != (revision, STAGING_SCHEMA_VERSION):
                return False
            rows = connection.execute(
                text(
                    "SELECT id, is_active FROM coach_catalog_exercise "
                    "WHERE id IN (:active_id, :inactive_id)"
                ),
                {
                    "active_id": STAGING_ACTIVE_EXERCISE_ID,
                    "inactive_id": STAGING_INACTIVE_EXERCISE_ID,
                },
            ).all()
            return {row.id: bool(row.is_active) for row in rows} == {
                STAGING_ACTIVE_EXERCISE_ID: True,
                STAGING_INACTIVE_EXERCISE_ID: False,
            }
    except SQLAlchemyError:
        return False
