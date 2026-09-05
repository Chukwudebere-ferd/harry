from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "harry"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/harry"
    # Used to build telegram_url and verification_url
    bot_username: str = "ExampleVerifyBot"
    api_base_url: str = "http://localhost:8000"

    verification_ttl_seconds: int = 300
    max_pending_per_project: int = 100
    # Simple in-process rate limit for creation endpoint
    rate_limit_per_minute: int = 20

    model_config = {"env_prefix": "HARRY_", "env_file": ".env"}


settings = Settings()
