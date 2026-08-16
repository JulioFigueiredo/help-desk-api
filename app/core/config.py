from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Help Desk SaaS"
    VERSION: str = "0.1.0"

    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/help_desk"
    )

    SECRET_KEY: str = "change-me-in-production-super-secret-key-123456"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
