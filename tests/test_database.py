"""URL normalization for an explicitly-declared SQL driver (NT-071)."""
from app.services.database import _normalize_database_url


def test_legacy_postgres_scheme_is_normalized_to_explicit_psycopg2_driver():
    url = "postgres://user:pass@host/db"
    assert _normalize_database_url(url) == "postgresql+psycopg2://user:pass@host/db"


def test_bare_postgresql_scheme_is_normalized_to_explicit_psycopg2_driver():
    url = "postgresql://user:pass@host/db?sslmode=require"
    assert (
        _normalize_database_url(url)
        == "postgresql+psycopg2://user:pass@host/db?sslmode=require"
    )


def test_already_explicit_driver_is_left_untouched():
    url = "postgresql+psycopg2://user:pass@host/db"
    assert _normalize_database_url(url) == url


def test_sqlite_url_is_left_untouched():
    url = "sqlite:///./data.db"
    assert _normalize_database_url(url) == url
