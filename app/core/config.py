from pydantic import BaseSettings, Field
from functools import lru_cache
from typing import List, Optional

class Settings(BaseSettings):
    app_name: str = "NexTarget API"
    environment: str = "dev"
    debug: bool = True

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

    # Database
    database_url: str = "sqlite:///./data.db"

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

    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore
