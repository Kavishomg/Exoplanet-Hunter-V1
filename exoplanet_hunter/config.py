from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EXOHUNTER_", env_file=".env", extra="ignore")

    data_dir: Path = Field(default=Path("data/uploads"))
    output_dir: Path = Field(default=Path("outputs"))
    max_upload_mb: int = 50
    allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:8000"])
    periodogram_method: Literal["auto", "bls", "lomb_scargle"] = "auto"
    minimum_points: int = 50
    output_ttl_hours: int = 168
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    api_key: str = ""
    plot_dpi: int = 100

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
