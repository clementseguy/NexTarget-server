"""Migration failures abort startup without leaking secrets (NT-071).

Uses an unreachable local port (nothing listens there) so the test runs
anywhere, without requiring a real PostgreSQL instance.
"""
import pytest
from sqlalchemy.exc import OperationalError

from app.core.config import get_settings
from scripts.run_migrations import run_migrations


def test_run_migrations_raises_when_database_is_unreachable(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(
        settings, "database_migration_url", "postgresql://user@localhost:1/nope"
    )

    # Connection refused surfaces as SQLAlchemy's OperationalError (wrapping psycopg2).
    with pytest.raises(OperationalError):
        run_migrations()
