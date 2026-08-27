"""Tests for the read-only administration page (NT-049)."""

import base64

import pytest
from sqlmodel import Session

from app.api import admin
from app.models.user import User
from app.services.admin_auth import hash_admin_password, verify_admin_password
from app.services.database import engine
from tests.conftest import client


ADMIN_PASSWORD = "correct horse battery staple"


@pytest.fixture
def admin_configured(monkeypatch):
    """Configure deterministic admin credentials with a fresh verifier."""
    monkeypatch.setattr(admin.settings, "admin_username", "operator")
    monkeypatch.setattr(
        admin.settings,
        "admin_password_hash",
        hash_admin_password(ADMIN_PASSWORD),
    )


@pytest.mark.asyncio
async def test_admin_access_without_credentials_is_refused(admin_configured):
    async with client() as ac:
        response = await ac.get("/app/admin/users")

    assert response.status_code == 401
    assert response.headers["www-authenticate"].startswith("Basic")
    assert response.headers["cache-control"] == "no-store, max-age=0"


@pytest.mark.asyncio
async def test_admin_access_with_wrong_credentials_is_refused(admin_configured):
    async with client() as ac:
        response = await ac.get(
            "/app/admin/users",
            auth=("operator", "wrong password"),
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_access_fails_closed_when_not_configured(monkeypatch):
    monkeypatch.setattr(admin.settings, "admin_username", None)
    monkeypatch.setattr(admin.settings, "admin_password_hash", None)

    async with client() as ac:
        response = await ac.get("/app/admin/users")

    assert response.status_code == 503
    assert response.headers["cache-control"] == "no-store, max-age=0"


@pytest.mark.asyncio
async def test_admin_can_read_existing_users_without_sensitive_data(admin_configured):
    with Session(engine) as session:
        session.add(
            User(
                id="google-user-id",
                email="alice@example.com",
                provider="google",
                display_name="Alice <Admin>",
                avatar_url="https://images.example.com/alice.png?size=40&crop=true",
            )
        )
        session.add(
            User(
                id="facebook-user-id",
                email="bob@example.com",
                provider="facebook",
                is_active=False,
            )
        )
        session.commit()

    async with client() as ac:
        response = await ac.get(
            "/app/admin/users",
            auth=("operator", ADMIN_PASSWORD),
        )

    assert response.status_code == 200
    assert "google-user-id" in response.text
    assert "alice@example.com" in response.text
    assert "Alice &lt;Admin&gt;" in response.text
    assert "Inactive" in response.text
    assert "Alice <Admin>" not in response.text
    assert "refresh_token" not in response.text
    assert admin.settings.admin_password_hash not in response.text
    assert response.headers["cache-control"] == "no-store, max-age=0"
    assert response.headers["x-robots-tag"] == "noindex, nofollow, noarchive"
    assert "default-src 'none'" in response.headers["content-security-policy"]


@pytest.mark.asyncio
async def test_admin_prefix_exposes_no_mutation_operation(admin_configured):
    auth_header = base64.b64encode(
        f"operator:{ADMIN_PASSWORD}".encode("utf-8")
    ).decode("ascii")
    headers = {"Authorization": f"Basic {auth_header}"}

    async with client() as ac:
        responses = [
            await ac.request(method, "/app/admin/users", headers=headers)
            for method in ("POST", "PUT", "PATCH", "DELETE")
        ]

    assert all(response.status_code == 405 for response in responses)


@pytest.mark.asyncio
async def test_admin_html_page_is_not_exposed_as_a_rest_api(admin_configured):
    """Keep the HTML screen outside the REST namespace and OpenAPI schema."""
    async with client() as ac:
        legacy_response = await ac.get(
            "/admin/users",
            auth=("operator", ADMIN_PASSWORD),
        )
        openapi_response = await ac.get("/openapi.json")

    assert legacy_response.status_code == 404
    assert "/app/admin/users" not in openapi_response.json()["paths"]


def test_admin_password_verifier_is_salted_and_fails_closed():
    first = hash_admin_password(ADMIN_PASSWORD)
    second = hash_admin_password(ADMIN_PASSWORD)

    assert first != second
    assert ADMIN_PASSWORD not in first
    assert verify_admin_password(ADMIN_PASSWORD, first)
    assert not verify_admin_password("wrong password", first)
    assert not verify_admin_password(ADMIN_PASSWORD, "malformed")
