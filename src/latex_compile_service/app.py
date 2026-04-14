from __future__ import annotations

from fastapi import FastAPI, Request
from loguru import logger
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from prometheus_client import Counter

from latex_compile_service.config import get_settings
from latex_compile_service.api.routers.compile import router as compile_router
from latex_compile_service.api.routers.health import router as health_router

REQUEST_COUNTER = Counter("latex_compile_requests_total", "Total compilation requests processed")
ERROR_COUNTER = Counter("latex_compile_errors_total", "Total failed compilation requests")


def create_app() -> FastAPI:
    settings = get_settings()

    logger.remove()
    logger.add(
        sink="sys.stderr",
        level="DEBUG" if settings.debug else "INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}</cyan> | <level>{message}</level>",
    )

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Secure LaTeX compilation API with Celery background execution.",
    )
    app.state.settings = settings
    app.state.request_counter = REQUEST_COUNTER
    app.state.error_counter = ERROR_COUNTER

    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.include_router(compile_router, prefix="/api/v1", tags=["compile"])
    app.include_router(health_router, prefix="/api/v1", tags=["health"])

    @app.middleware("http")
    async def count_requests(request: Request, call_next):
        REQUEST_COUNTER.inc()
        response = await call_next(request)
        return response

    return app


app = create_app()
