from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import get_settings
from .services.database import init_db
from .api import auth_google, auth_facebook, auth_token, users, coach

settings = get_settings()

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

@app.on_event("startup")
def on_startup():
    init_db()

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
