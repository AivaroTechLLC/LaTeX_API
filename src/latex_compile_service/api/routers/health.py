from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from prometheus_client import generate_latest

from latex_compile_service.api.dependencies import get_settings_dep
from latex_compile_service.config import Settings

router = APIRouter()


@router.get("/health")
def health(settings: Settings = Depends(get_settings_dep)) -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@router.get("/metrics", response_class=PlainTextResponse)
def metrics(settings: Settings = Depends(get_settings_dep)) -> str:
    if not settings.enable_prometheus:
        return "# Prometheus metrics are disabled.\n"

    return generate_latest().decode("utf-8")
