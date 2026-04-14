from __future__ import annotations

import base64
from celery.utils.log import get_task_logger
from latex_compile_service.celery_app import celery
from latex_compile_service.config import get_settings
from latex_compile_service.services.compile_service import LatexCompiler

logger = get_task_logger(__name__)


@celery.task(bind=True, name="latex_compile_service.compile_tex", max_retries=2, default_retry_delay=5)
def compile_tex_task(
    self,
    filename: str,
    payload_b64: str,
    main_tex: str | None,
    engine: str,
    shell_escape: bool,
    timeout: int,
) -> dict:
    request_id = None
    if getattr(self.request, "headers", None) is not None:
        request_id = self.request.headers.get("request_id")
    request_id = request_id or "unknown"

    settings = get_settings()
    logger.info(
        "Starting LaTeX compile task for %s [request_id=%s]",
        filename,
        request_id,
    )
    compiler = LatexCompiler(settings)
    content = base64.b64decode(payload_b64)

    try:
        result = compiler.compile_source_bytes(
            filename=filename,
            content=content,
            main_tex=main_tex,
            engine=engine,
            shell_escape=shell_escape,
            timeout=timeout,
        )
    except (OSError, MemoryError) as exc:
        logger.warning(
            "Retrying LaTeX compile task for %s [request_id=%s] after transient error: %s",
            filename,
            request_id,
            exc,
        )
        raise self.retry(exc=exc, countdown=5)

    logger.info(
        "LaTeX compile task completed for %s [request_id=%s]: %s",
        filename,
        request_id,
        result.get("status"),
    )
    return result
