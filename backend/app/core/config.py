from functools import lru_cache
from typing import Optional
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
    supabase_jwt_secret: str

    # AWS S3 configuration
    aws_profile: Optional[str] = None
    aws_region: str = "us-east-1"
    s3_enrollment_bucket: str = "faceit-uploads-dev"
    s3_presigned_url_expiry: int = 3600  # 1 hour
    s3_attendance_bucket: str = "faceit-uploads-dev"
    s3_attendance_presigned_url_expiry: int = 300  # 5 minutes

    # AWS SQS configuration
    sqs_enrollment_queue_url: Optional[str] = None
    sqs_attendance_queue_url: Optional[str] = None
    sqs_max_messages: int = 5
    sqs_wait_time_seconds: int = 10

    # Worker runtime configuration
    worker_max_empty_polls: int = 3
    worker_poll_sleep_seconds: int = 2
    worker_embedding_mode: str = "v1"

    # CORS configuration (comma-separated list of allowed origins)
    cors_allow_origins: str = (
        "http://localhost:8081,"
        "http://127.0.0.1:8081,"
        "http://localhost:19006,"
        "http://127.0.0.1:19006,"
        "http://localhost:3000,"
        "http://127.0.0.1:3000"
    )

    def parsed_cors_allow_origins(self) -> list[str]:
        """Return configured CORS origins as a cleaned list."""
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
