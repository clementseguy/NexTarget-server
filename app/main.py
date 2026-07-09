import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .core.config import get_settings
from .core.logging import get_logger, request_id_var, setup_logging
from .services.database import init_db
from .api import auth_google, auth_facebook, auth_token, users, coach

settings = get_settings()

# Structured JSON logging (NT-053).
setup_logging(level=settings.log_level)
logger = get_logger("nextarget.http")

app = FastAPI(title=settings.app_name, debug=settings.debug)

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


@app.on_event("startup")
def on_startup():
    init_db()
    logger.info("startup", extra={"environment": settings.environment})


@app.get("/health")
async def health():
    return {"status": "ok"}

# OAuth authentication routers
app.include_router(auth_google.router)
app.include_router(auth_facebook.router)
app.include_router(auth_token.router)

# User management router
app.include_router(users.router)

# Coach IA (proxy Mistral)
app.include_router(coach.router)
