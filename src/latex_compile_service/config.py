from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field("latex-compile-service")
    debug: bool = Field(False)
    host: str = Field("0.0.0.0")
    port: int = Field(8000)
    api_key: str = Field(...)

    redis_url: str = Field("redis://redis:6379/0")
    celery_broker_url: str = Field("redis://redis:6379/0")
    celery_result_backend: str = Field("redis://redis:6379/1")

    max_upload_size_mb: int = Field(20)
    compile_timeout: int = Field(120)
    rate_limit: str = Field("20/minute")
    default_engine: str = Field("pdflatex")
    allow_shell_escape: bool = Field(False)
    enable_prometheus: bool = Field(True)
    allowed_engines: list[str] = Field(["pdflatex", "xelatex", "lualatex"])
    allowed_extensions: list[str] = Field([".tex", ".zip"])

    data_dir: Path = Field(Path("/app/data"))
    latexmk_binary: str = Field("latexmk")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
