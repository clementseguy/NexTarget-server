"""Tests for the public, static NexTarget landing page."""
import base64
import hashlib
import re

from tests.conftest import client


async def test_landing_is_public_static_and_has_security_headers():
    async with client() as ac:
        response = await ac.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<h1" in response.text
    assert response.text.count("<h1") == 1
    assert "NexTarget" in response.text
    assert "https://github.com/clementseguy/NexTarget-app" in response.text
    assert "__ROBOTS_DIRECTIVE__" not in response.text
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "unsafe-inline" not in response.headers["content-security-policy"]
    assert "unsafe-eval" not in response.headers["content-security-policy"]
    assert "*" not in response.headers["content-security-policy"]


async def test_landing_json_ld_is_allowed_by_its_csp_hash():
    async with client() as ac:
        response = await ac.get("/")

    match = re.search(
        r'<script type="application/ld\+json">(?P<body>.*?)</script>',
        response.text,
        flags=re.DOTALL,
    )
    assert match is not None
    digest = base64.b64encode(
        hashlib.sha256(match.group("body").encode("utf-8")).digest()
    ).decode("ascii")
    assert f"'sha256-{digest}'" in response.headers["content-security-policy"]


async def test_non_production_hosts_are_not_indexable():
    async with client() as ac:
        landing = await ac.get("/")
        robots = await ac.get("/robots.txt")
        sitemap = await ac.get("/sitemap.xml")

    assert '<meta name="robots" content="noindex, nofollow, noarchive">' in landing.text
    assert landing.headers["x-robots-tag"] == "noindex, nofollow, noarchive"
    assert robots.text == "User-agent: *\nDisallow: /\n"
    assert sitemap.headers["x-robots-tag"] == "noindex, nofollow, noarchive"
    assert "https://nextarget-server.onrender.com/" in sitemap.text


async def test_canonical_production_host_is_indexable(monkeypatch):
    from app import main

    monkeypatch.setattr(main.settings, "environment", "production")

    async with client() as ac:
        landing = await ac.get(
            "/", headers={"host": "nextarget-server.onrender.com"}
        )
        robots = await ac.get(
            "/robots.txt", headers={"host": "nextarget-server.onrender.com"}
        )

    assert '<meta name="robots" content="index, follow">' in landing.text
    assert landing.headers["x-robots-tag"] == "index, follow"
    assert "Allow: /" in robots.text
    assert "Sitemap: https://nextarget-server.onrender.com/sitemap.xml" in robots.text


async def test_spoofed_or_malformed_hosts_stay_noindex(monkeypatch):
    from app import main

    monkeypatch.setattr(main.settings, "environment", "production")

    async with client() as ac:
        preview = await ac.get("/", headers={"host": "preview-123.onrender.com"})
        malformed = await ac.get(
            "/", headers={"host": "nextarget-server.onrender.com/preview"}
        )

    assert preview.headers["x-robots-tag"] == "noindex, nofollow, noarchive"
    assert malformed.headers["x-robots-tag"] == "noindex, nofollow, noarchive"


async def test_landing_rejects_unused_http_methods():
    async with client() as ac:
        response = await ac.post("/")

    assert response.status_code == 405


async def test_static_assets_are_local_and_cacheable():
    async with client() as ac:
        css = await ac.get("/site-assets/styles.css")
        logo = await ac.get("/site-assets/logo.webp")
        template = await ac.get("/site-assets/index.html")

    assert css.status_code == 200
    assert logo.status_code == 200
    assert template.status_code == 404
    assert css.headers["content-type"].startswith("text/css")
    assert logo.headers["content-type"] == "image/webp"
    assert css.headers["cache-control"] == "public, max-age=604800"
    assert logo.headers["x-content-type-options"] == "nosniff"
