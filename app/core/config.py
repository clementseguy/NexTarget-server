import re
from functools import lru_cache
from typing import Any, Dict, List, Optional

from pydantic import BaseSettings, Field, root_validator

STAGING_DATABASE_URL = "sqlite:////data/nextarget-staging.db"
STAGING_REVISION_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class Settings(BaseSettings):
    app_name: str = "NexTarget API"
    environment: str = "dev"
    debug: bool = True
    source_revision: Optional[str] = Field(default=None, env="NEXTARGET_SOURCE_REVISION")

    # Logging (NT-053): niveau du logger applicatif JSON.
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # CORS (NT-065): comma-separated list of allowed origins.
    # If unset, defaults depend on the environment:
    #   - dev: ["*"] (permissive, local tooling / Swagger UI)
    #   - anything else (e.g. production): [] — no cross-origin browser
    #     access. The mobile app is unaffected (native HTTP calls do not
    #     send an Origin header); add a web client origin here if one
    #     ever exists.
    cors_allow_origins: Optional[str] = Field(default=None, env="CORS_ALLOW_ORIGINS")

    @property
    def cors_origins(self) -> List[str]:
        if self.cors_allow_origins is not None:
            return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]
        return ["*"] if self.environment == "dev" else []

    # Security / Auth
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    access_token_exp_minutes: int = 60
    callback_token_exp_minutes: int = 10  # Short-lived token for OAuth callback
    refresh_token_exp_days: int = 30  # Refresh token lifetime (NT-048)

    # Read-only administration (NT-049). The password itself is never stored:
    # ADMIN_PASSWORD_HASH contains a salted scrypt verifier generated locally.
    admin_username: Optional[str] = Field(default=None, env="ADMIN_USERNAME")
    admin_password_hash: Optional[str] = Field(default=None, env="ADMIN_PASSWORD_HASH")

    # Database (NT-071)
    # DATABASE_URL: runtime connection used by the app (pooled, least-privilege
    # role in production — e.g. Neon's pooled endpoint). Defaults to a local
    # SQLite file for dev/tests.
    database_url: str = "sqlite:///./data.db"
    # DATABASE_MIGRATION_URL: direct connection used only by Alembic and
    # administrative operations (owner role, unpooled — required by Neon for
    # DDL). Falls back to DATABASE_URL when unset (e.g. local SQLite).
    database_migration_url: Optional[str] = Field(default=None, env="DATABASE_MIGRATION_URL")

    # Mistral
    mistral_api_key: Optional[str] = Field(default=None, env="MISTRAL_API_KEY")
    mistral_api_base: str = "https://api.mistral.ai/v1"
    mistral_model: str = "mistral-small-latest"
    mistral_timeout_seconds: int = 30

    # Google OAuth
    google_client_id: Optional[str] = Field(default=None, env="GOOGLE_CLIENT_ID")
    google_client_secret: Optional[str] = Field(default=None, env="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: Optional[str] = Field(default=None, env="GOOGLE_REDIRECT_URI")

    # Facebook OAuth
    facebook_client_id: Optional[str] = Field(default=None, env="FACEBOOK_CLIENT_ID")
    facebook_client_secret: Optional[str] = Field(default=None, env="FACEBOOK_CLIENT_SECRET")
    facebook_redirect_uri: Optional[str] = Field(default=None, env="FACEBOOK_REDIRECT_URI")

    @root_validator
    def validate_local_staging(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Refuse an unsafe runtime before it can open a staging database."""
        if values.get("environment") != "staging":
            return values
        if values.get("database_url") != STAGING_DATABASE_URL:
            raise ValueError("Invalid local staging configuration: database_url")
        if values.get("database_migration_url") != STAGING_DATABASE_URL:
            raise ValueError("Invalid local staging configuration: migration database")
        if values.get("debug") is not False:
            raise ValueError("Invalid local staging configuration: debug")
        if values.get("cors_allow_origins") not in (None, ""):
            raise ValueError("Invalid local staging configuration: CORS origins")
        revision = values.get("source_revision") or ""
        if not STAGING_REVISION_PATTERN.fullmatch(revision):
            raise ValueError("Invalid local staging configuration: source revision")
        secret = values.get("jwt_secret_key") or ""
        if len(secret) < 32 or secret.startswith("replace-with-"):
            raise ValueError("Invalid local staging configuration: JWT secret")
        return values

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore
