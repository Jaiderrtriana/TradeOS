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

    # TRADEOS_API_SPECIFICATION.md §4.1 requires a "longer-lived" refresh
    # token but names no exact duration — 30 days is a documented
    # implementation default (CHANGELOG.md, Sprint 1.1), not a value the
    # spec states explicitly.
    refresh_token_expire_days: int = 30

    # No frozen document specifies CORS — a pure browser-security
    # mechanism, not an architectural/domain/API decision, required for
    # any browser-based frontend to reach this backend at all
    # (TRADEOS_SYSTEM_ARCHITECTURE.md §12.1: frontend and backend are
    # served independently, i.e. cross-origin by construction). Default
    # matches Vite's dev server port; override for any other environment.
    cors_allowed_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
