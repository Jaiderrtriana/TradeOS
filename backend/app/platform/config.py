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


settings = Settings()
