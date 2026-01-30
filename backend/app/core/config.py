from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Supabase configuration
    supabase_url: str
    supabase_service_key: str


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
