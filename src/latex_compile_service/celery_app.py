from __future__ import annotations

from celery import Celery
from latex_compile_service.config import get_settings

settings = get_settings()

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
    include=["latex_compile_service.tasks"],
)
