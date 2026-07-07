"""Tests for CORS configuration per environment (NT-065)."""
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings, get_settings
from app.main import app


def _settings(**overrides) -> Settings:
    # jwt_secret_key is required; other values may still be read from .env,
    # but explicitly passed fields always win.
    return Settings(jwt_secret_key="test-secret", **overrides)


def test_dev_defaults_to_wildcard():
    s = _settings(environment="dev", cors_allow_origins=None)
    assert s.cors_origins == ["*"]


def test_production_defaults_to_no_origins():
    s = _settings(environment="production", cors_allow_origins=None)
    assert s.cors_origins == []


def test_explicit_origins_parsed_from_comma_separated_string():
    s = _settings(
        environment="production",
        cors_allow_origins="https://app.nextarget.fr, https://admin.nextarget.fr",
    )
    assert s.cors_origins == [
        "https://app.nextarget.fr",
        "https://admin.nextarget.fr",
    ]


def test_explicit_origins_override_dev_wildcard():
    s = _settings(environment="dev", cors_allow_origins="http://localhost:5173")
    assert s.cors_origins == ["http://localhost:5173"]


def test_empty_string_means_no_origins_even_in_dev():
    s = _settings(environment="dev", cors_allow_origins="")
    assert s.cors_origins == []


def test_app_middleware_uses_settings_origins():
    cors = next(
        m for m in app.user_middleware if m.cls is CORSMiddleware
    )
    assert cors.kwargs["allow_origins"] == get_settings().cors_origins
