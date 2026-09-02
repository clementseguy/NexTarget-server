"""Migration failures abort startup without leaking secrets (NT-071).

Uses an unreachable local port (nothing listens there) so the test runs
anywhere, without requiring a real PostgreSQL instance.
"""
import pytest

from app.core.config import get_settings
from scripts.run_migrations import run_migrations


def test_run_migrations_raises_when_database_is_unreachable(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(
        settings, "database_migration_url", "postgresql://user@localhost:1/nope"
    )

    with pytest.raises(Exception):
        run_migrations()
