"""Configuration management for workers."""
import os
from pydantic import Field
from pydantic_settings import BaseSettings
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

_ENV_FILE = Path(__file__).resolve().parents[3] / '.env'


class Settings(BaseSettings):
    """Application settings."""

    # Database
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/post_generator",
        alias="DATABASE_URL"
    )
    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")
    db_name: str = Field(default="post_generator", alias="DB_NAME")
    db_user: str = Field(default="postgres", alias="DB_USER")
    db_password: str = Field(default="", alias="DB_PASSWORD")

    # Redis
    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_password: str | None = Field(default=None, alias="REDIS_PASSWORD")

    # Embedding provider: "openai" or "gemini"
    embedding_provider: str = Field(default="openai", alias="EMBEDDING_PROVIDER")
    embedding_model: str | None = Field(default=None, alias="EMBEDDING_MODEL")
    embedding_dimension: int | None = Field(default=None, alias="EMBEDDING_DIMENSION")

    # OpenAI
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")

    # Google Gemini
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")

    # LlamaParse
    llama_cloud_api_key: str | None = Field(default=None, alias="LLAMA_CLOUD_API_KEY")

    # Worker
    worker_concurrency: int = Field(default=5, alias="WORKER_CONCURRENCY")

    # Pydantic v2 model config: load env from repo root and ignore unknown env keys
    model_config = {
        "env_file": str(_ENV_FILE),
        "case_sensitive": False,
        "extra": "ignore",
    }


# Global settings instance
settings = Settings()

# --- Startup diagnostics (use print so they show before logging is configured) ---
if _ENV_FILE.exists():
    print(f"[config] Loaded .env from: {_ENV_FILE}")
else:
    print(f"[config] WARNING: .env NOT FOUND at: {_ENV_FILE}")
    print("[config]   -> copy .env.example to .env and fill in your keys!")

print(f"[config] EMBEDDING_PROVIDER={settings.embedding_provider}")

if settings.embedding_provider == "gemini" and not settings.gemini_api_key:
    print("[config] ERROR: EMBEDDING_PROVIDER=gemini but GEMINI_API_KEY is not set!")
elif settings.embedding_provider == "openai" and not settings.openai_api_key:
    print("[config] ERROR: EMBEDDING_PROVIDER=openai but OPENAI_API_KEY is not set!")


def get_database_url() -> str:
    """Get database connection URL."""
    if settings.database_url:
        return settings.database_url
    return f"postgresql://{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/{settings.db_name}"


def get_redis_url() -> str:
    """Get Redis connection URL."""
    if settings.redis_password:
        return f"redis://:{settings.redis_password}@{settings.redis_host}:{settings.redis_port}/0"
    return f"redis://{settings.redis_host}:{settings.redis_port}/0"
