"""Local QA settings must fail before opening an unsafe database."""

import pytest
from pydantic import ValidationError

from app.core.config import STAGING_DATABASE_URL, Settings


def _settings(**overrides):
    values = {
        "environment": "staging",
        "debug": False,
        "database_url": STAGING_DATABASE_URL,
        "database_migration_url": STAGING_DATABASE_URL,
        "source_revision": "a" * 40,
        "jwt_secret_key": "s" * 32,
        "cors_allow_origins": "",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_local_staging_settings_are_accepted():
    assert _settings().environment == "staging"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("database_url", "postgresql://example.invalid/prod"),
        ("database_migration_url", "postgresql://example.invalid/prod"),
        ("debug", True),
        ("cors_allow_origins", "*"),
        ("source_revision", "unknown"),
        ("jwt_secret_key", "replace-with-a-local-random-secret-of-at-least-32-characters"),
    ],
)
def test_local_staging_rejects_unsafe_settings(field, value):
    with pytest.raises(ValidationError, match="Invalid local staging configuration"):
        _settings(**{field: value})
