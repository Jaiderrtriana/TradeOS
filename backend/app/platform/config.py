"""
Platform: application configuration.

Typed, environment-variable-backed settings via pydantic-settings — the
official choice for Configuration Management (TRADEOS_TECHNICAL_STACK.md
§7), replacing untyped os.environ lookups scattered through the codebase.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://tradeos:tradeos@localhost:5432/tradeos"

    # TRADEOS_SYSTEM_ARCHITECTURE.md ADR-07 (token-based auth). Default is a
    # dev-only placeholder — TRADEOS_SYSTEM_ARCHITECTURE.md §11.1 requires
    # secrets be injected via environment configuration, never committed;
    # override via JWT_SECRET_KEY in any real environment.
    jwt_secret_key: str = "dev-only-insecure-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30


settings = Settings()
