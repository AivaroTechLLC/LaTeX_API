from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from pydantic import Field, field_validator
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
    max_memory_mb: int = Field(512)
    max_log_chars: int = Field(100_000)
    celery_result_expires: int = Field(3600)
    trusted_proxy_ips: list[str] = Field([])
    rate_limit: str = Field("20/minute")
    default_engine: str = Field("pdflatex")
    allow_shell_escape: bool = Field(False)
    enable_prometheus: bool = Field(True)
    allowed_engines: list[str] = Field(["pdflatex", "xelatex", "lualatex"])
    allowed_extensions: list[str] = Field([".tex", ".zip"])

    @field_validator("allowed_engines", mode="before")
    @classmethod
    def parse_allowed_engines(cls, v):
        if isinstance(v, str):
            return [engine.strip() for engine in v.split(",") if engine.strip()]
        return v

    @field_validator("allowed_extensions", mode="before")
    @classmethod
    def parse_allowed_extensions(cls, v):
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(",") if ext.strip()]
        return v

    @field_validator("api_key")
    @classmethod
    def api_key_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError(
                "API_KEY must be set to a non-empty value. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        return v

    data_dir: Path = Field(Path("/app/data"))
    latexmk_binary: str = Field("latexmk")
    # Comma-separated list of allowed CORS origins.
    # Set to "*" only for fully public, read-only APIs.
    # For this service, set explicitly in .env (e.g. CORS_ORIGINS=https://yourapp.com)
    cors_origins: list[str] = Field([])

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("trusted_proxy_ips", mode="before")
    @classmethod
    def parse_trusted_proxy_ips(cls, v):
        if isinstance(v, str):
            return [ip.strip() for ip in v.split(",") if ip.strip()]
        return v

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
