"""
Centralized application configuration for RetailSense AI.
Loads variables from environment or .env file using pydantic-settings.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Strongly-typed application settings."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- LLM Configuration ----
    llm_api_key: str = Field(default="", description="Grok or Groq API Key")
    llm_api_url: str = Field(
        default="https://api.groq.com/openai/v1",
        description="LLM endpoint URL (e.g., https://api.x.ai/v1 for Grok)",
    )
    llm_model_name: str = Field(
        default="llama-3.3-70b-versatile",
        description="Model identifier (e.g. grok-2-1212 or llama-3.3-70b-versatile)",
    )
    llm_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=1024, gt=0)

    # ---- Storage Paths (relative to project root) ----
    data_dir: Path = Field(default=Path("data"))
    raw_dir: Path = Field(default=Path("data/raw"))
    bronze_dir: Path = Field(default=Path("data/bronze"))
    silver_dir: Path = Field(default=Path("data/silver"))
    gold_dir: Path = Field(default=Path("data/gold"))
    models_dir: Path = Field(default=Path("models"))
    log_file: Path = Field(default=Path("logs/app.log"))

    # ---- ETL & Spark settings ----
    sample_limit: int = Field(
        default=100,
        description="Max items to process from sales dataset (0 = no limit, useful for fast local testing)",
    )
    spark_local_ip: str = Field(default="127.0.0.1")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO"
    )

    # ---- API server ----
    api_host: str = Field(default="127.0.0.1")
    api_port: int = Field(default=8000)
    api_base_url: str = Field(default="http://localhost:8000")

    @field_validator(
        "data_dir",
        "raw_dir",
        "bronze_dir",
        "silver_dir",
        "gold_dir",
        "models_dir",
        "log_file",
        mode="after",
    )
    @classmethod
    def _resolve_path(cls, v: Path) -> Path:
        """Resolve relative paths against the project root."""
        return v if v.is_absolute() else (PROJECT_ROOT / v).resolve()

    def ensure_dirs(self) -> None:
        """Ensure all required data, model, and log directories exist."""
        for p in (
            self.data_dir,
            self.raw_dir,
            self.bronze_dir,
            self.silver_dir,
            self.gold_dir,
            self.models_dir,
            self.log_file.parent,
        ):
            p.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retrieve settings singleton."""
    s = Settings()
    s.ensure_dirs()
    return s


settings = get_settings()
