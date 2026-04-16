from __future__ import annotations

from celery import Celery

try:
    from latex_compile_service.config import get_settings

    settings = get_settings()
except Exception as exc:
    raise RuntimeError(
        "Failed to initialize Celery configuration for latex_compile_service. "
        "Check environment variables, .env file, and project imports."
    ) from exc

celery = Celery(
    "latex_compile_service",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_soft_time_limit=settings.compile_timeout + 20,
    task_time_limit=settings.compile_timeout + 30,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    broker_transport_options={"visibility_timeout": settings.compile_timeout + 60},
    result_expires=settings.celery_result_expires,
    result_compression="gzip",
    include=["latex_compile_service.tasks"],
)
