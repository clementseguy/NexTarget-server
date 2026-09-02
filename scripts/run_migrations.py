#!/usr/bin/env python
"""Apply pending Alembic migrations (NT-071).

Invoked before Uvicorn starts (see `start.py`, Render's start command) so a
broken migration blocks deployment instead of serving traffic against a
stale/partial schema. Never logs the connection string, host or credentials:
on failure only the exception *type* is reported, which is enough to point an
operator at Render/Neon logs without leaking secrets.

Usage: `python scripts/run_migrations.py` (also callable as `run_migrations()`).
"""
import logging
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

logger = logging.getLogger("nextarget.migrations")

REPO_ROOT = Path(__file__).resolve().parent.parent


def run_migrations() -> None:
    """Run `alembic upgrade head` against DATABASE_MIGRATION_URL/DATABASE_URL."""
    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(REPO_ROOT / "alembic"))
    command.upgrade(cfg, "head")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    try:
        run_migrations()
    except Exception as exc:  # noqa: BLE001
        # Deliberately broad: any failure must block startup, see module docstring.
        logger.error("Database migration failed (%s); aborting startup", type(exc).__name__)
        sys.exit(1)
    logger.info("Database migrations applied successfully")
