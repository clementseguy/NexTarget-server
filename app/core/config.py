from pydantic import BaseSettings, Field
from functools import lru_cache
from typing import Optional

class Settings(BaseSettings):
    app_name: str = "NexTarget API"
    environment: str = "dev"
    debug: bool = True

    # Security / Auth
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    access_token_exp_minutes: int = 60

    # Database
    database_url: str = "sqlite:///./data.db"

    # Mistral
    mistral_api_key: Optional[str] = Field(default=None, env="MISTRAL_API_KEY")
    mistral_api_base: str = "https://api.mistral.ai/v1"
    mistral_model: str = "mistral-small-latest"
    mistral_timeout_seconds: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore
