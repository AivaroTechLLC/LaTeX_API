from __future__ import annotations

import shutil

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import generate_latest

from latex_compile_service.api.dependencies import get_settings_dep
from latex_compile_service.config import Settings

router = APIRouter()


@router.get("/health")
async def health(settings: Settings = Depends(get_settings_dep)) -> JSONResponse:
    redis_status = "ok"
    latexmk_status = "ok"

    try:
        async with aioredis.from_url(settings.redis_url) as redis_client:
            if not await redis_client.ping():
                redis_status = "error"
    except Exception:
        redis_status = "error"

    if shutil.which(settings.latexmk_binary) is None:
        latexmk_status = "error"

    status_code = status.HTTP_200_OK if redis_status == "ok" and latexmk_status == "ok" else status.HTTP_503_SERVICE_UNAVAILABLE
    health_data = {
        "status": "ok" if status_code == status.HTTP_200_OK else "degraded",
        "redis": redis_status,
        "latexmk": latexmk_status,
    }

    return JSONResponse(status_code=status_code, content=health_data)


@router.get("/metrics", response_class=PlainTextResponse)
def metrics(settings: Settings = Depends(get_settings_dep)) -> str:
    if not settings.enable_prometheus:
        return "# Prometheus metrics are disabled.\n"

    return generate_latest().decode("utf-8")
