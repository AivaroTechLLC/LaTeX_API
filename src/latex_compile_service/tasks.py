from __future__ import annotations

import base64
from celery.utils.log import get_task_logger
from latex_compile_service.celery_app import celery
from latex_compile_service.config import get_settings
from latex_compile_service.services.compile_service import LatexCompiler

logger = get_task_logger(__name__)


@celery.task(bind=True, name="latex_compile_service.compile_tex")
def compile_tex_task(
    self,
    filename: str,
    payload_b64: str,
    main_tex: str | None,
    engine: str,
    shell_escape: bool,
    timeout: int,
) -> dict:
    settings = get_settings()
    logger.info("Starting LaTeX compile task for %s", filename)
    compiler = LatexCompiler(settings)
    content = base64.b64decode(payload_b64)
    result = compiler.compile_source_bytes(
        filename=filename,
        content=content,
        main_tex=main_tex,
        engine=engine,
        shell_escape=shell_escape,
        timeout=timeout,
    )
    logger.info("LaTeX compile task completed for %s: %s", filename, result.get("status"))
    return result
