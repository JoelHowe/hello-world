from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite:///./data/nuzzle.db"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    window_hours: int = 24
    max_posts_per_refresh: int = 5000
    default_trending_limit: int = Field(default=50, ge=1, le=500)
    min_sharers: int = Field(default=2, ge=1)

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
