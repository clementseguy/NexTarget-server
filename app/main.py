import base64
import hashlib
import re
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles

from .core.config import get_settings
from .core.logging import get_logger, request_id_var, setup_logging
from .services.database import init_db
from .api import admin, auth_google, auth_facebook, auth_token, coach, exercises, users

settings = get_settings()

# Public landing page. Only this dedicated directory is exposed; application
# sources, configuration and other repository files remain unreachable.
LANDING_DIR = Path(__file__).resolve().parent / "static" / "landing"
LANDING_TEMPLATE = (
    Path(__file__).resolve().parent / "templates" / "landing.html"
).read_text(encoding="utf-8")
PUBLIC_BASE_URL = "https://nextarget-server.onrender.com"
PRODUCTION_HOST = "nextarget-server.onrender.com"

_json_ld_match = re.search(
    r'<script type="application/ld\+json">(?P<body>.*?)</script>',
    LANDING_TEMPLATE,
    flags=re.DOTALL,
)
if _json_ld_match is None:
    raise RuntimeError("Landing page JSON-LD block is missing")
_json_ld_hash = base64.b64encode(
    hashlib.sha256(_json_ld_match.group("body").encode("utf-8")).digest()
).decode("ascii")
LANDING_CSP = (
    "default-src 'self'; "
    "base-uri 'none'; "
    "object-src 'none'; "
    "frame-ancestors 'none'; "
    "form-action 'none'; "
    "connect-src 'none'; "
    "font-src 'self'; "
    "img-src 'self'; "
    f"script-src 'sha256-{_json_ld_hash}'; "
    "style-src 'self'"
)

# Structured JSON logging (NT-053).
setup_logging(level=settings.log_level)
logger = get_logger("nextarget.http")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Initialize application resources on startup."""
    init_db()
    logger.info("startup", extra={"environment": settings.environment})
    yield


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)
app.mount("/site-assets", StaticFiles(directory=LANDING_DIR), name="site-assets")

# CORS (NT-065): origins are environment-driven — "*" in dev, none in
# production unless CORS_ALLOW_ORIGINS is explicitly configured.
# See Settings.cors_origins in core/config.py.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_correlation(request: Request, call_next):
    """Correlate and log every request (NT-053).

    - Accepts an inbound X-Request-ID (proxy/gateway) or generates one.
    - Exposes it to all handlers via a ContextVar (picked up by the JSON
      formatter) and echoes it in the response header.
    - Emits one structured log line per request: method, path, status,
      duration. Query strings are not logged (may carry OAuth codes/state).
    """
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:16]
    token = request_id_var.set(request_id)
    start = time.perf_counter()
    try:
        response = await call_next(request)
        logger.info(
            "request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round((time.perf_counter() - start) * 1000, 1),
            },
        )
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception:
        logger.exception(
            "request failed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": 500,
                "duration_ms": round((time.perf_counter() - start) * 1000, 1),
            },
        )
        raise
    finally:
        request_id_var.reset(token)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Apply conservative browser security headers without changing API logic."""
    response = await call_next(request)
    request_path = str(request.scope.get("path", ""))
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
    )
    response.headers["X-Frame-Options"] = "DENY"

    if settings.environment == "production":
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

    if request_path == "/" or request_path.startswith("/site-assets/"):
        response.headers["Content-Security-Policy"] = LANDING_CSP

    if request_path.startswith("/site-assets/") and response.status_code == 200:
        response.headers["Cache-Control"] = "public, max-age=604800"

    if request_path == "/app/admin" or request_path.startswith("/app/admin/"):
        for header, value in admin.ADMIN_HEADERS.items():
            response.headers[header] = value

    return response


@app.get("/health")
async def health():
    return {"status": "ok"}


def _is_public_production(request: Request) -> bool:
    """Return whether the request targets the canonical production host."""
    # Do not use request.url.hostname here. Pinned Starlette 0.37.2 reconstructs
    # request.url from untrusted input (PYSEC-2026-161/248). An exact raw Host
    # match is both sufficient for Render and fail-closed for previews.
    host = request.headers.get("host", "").lower().rstrip(".")
    return (
        settings.environment == "production"
        and host == PRODUCTION_HOST
    )


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def landing_page(request: Request) -> HTMLResponse:
    """Serve the public, database-free NexTarget landing page."""
    indexable = _is_public_production(request)
    robots = "index, follow" if indexable else "noindex, nofollow, noarchive"
    response = HTMLResponse(
        LANDING_TEMPLATE.replace("__ROBOTS_DIRECTIVE__", robots)
    )
    response.headers["X-Robots-Tag"] = robots
    return response


@app.get("/robots.txt", response_class=PlainTextResponse, include_in_schema=False)
async def robots_txt(request: Request) -> PlainTextResponse:
    """Allow indexing only on the canonical production host."""
    if _is_public_production(request):
        content = f"User-agent: *\nAllow: /\nSitemap: {PUBLIC_BASE_URL}/sitemap.xml\n"
    else:
        content = "User-agent: *\nDisallow: /\n"
    return PlainTextResponse(content)


@app.get("/sitemap.xml", include_in_schema=False)
async def sitemap_xml(request: Request) -> Response:
    """Expose a minimal sitemap while keeping non-production hosts noindex."""
    content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{PUBLIC_BASE_URL}/</loc></url>\n"
        "</urlset>\n"
    )
    response = Response(content=content, media_type="application/xml")
    if not _is_public_production(request):
        response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    return response


# OAuth authentication routers
app.include_router(auth_google.router)
app.include_router(auth_facebook.router)
app.include_router(auth_token.router)

# User management router
app.include_router(users.router)

# Coach IA (proxy Mistral)
app.include_router(coach.router)

# Read-only Coach exercise catalog
app.include_router(exercises.router)

# Read-only administration (NT-049)
app.include_router(admin.router)
