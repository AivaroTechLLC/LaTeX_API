import asyncio
import base64
from celery.result import AsyncResult
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import Any

from celery.exceptions import CeleryError
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from loguru import logger

from latex_compile_service.api.dependencies import get_settings_dep
from latex_compile_service.celery_app import celery
from latex_compile_service.config import Settings
from latex_compile_service.core.security import api_key_auth, virus_scan_stub
from latex_compile_service.schemas.compile import (
    CompileResponse,
    TaskStatusResponse,
    TaskSubmissionResponse,
)
from latex_compile_service.tasks import compile_tex_task

router = APIRouter()


@dataclass
class CompileRequest:
    content: bytes
    filename: str
    extension: str
    main_tex: str | None
    engine: str
    shell_escape: bool
    task_timeout: int
    encoded_payload: str


async def validate_compile_request(
    file: UploadFile = File(...),
    main_tex: str | None = Form(None),
    engine: str = Form("pdflatex"),
    shell_escape: bool = Form(False),
    timeout: int | None = Form(None),
    settings: Settings = Depends(get_settings_dep),
) -> CompileRequest:
    filename = file.filename or "upload.tex"
    extension = Path(filename).suffix.lower()

    if extension not in {".tex", ".zip"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .tex and .zip uploads are accepted.",
        )

    content = await file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Upload exceeds maximum size of {settings.max_upload_size_mb} MB.",
        )

    if not virus_scan_stub(content):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file failed security validation.",
        )

    if extension == ".zip" and not main_tex:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="main_tex is required when uploading a ZIP archive.",
        )

    engine = engine.lower()
    if engine not in settings.allowed_engines:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported engine '{engine}'. Allowed values: {', '.join(settings.allowed_engines)}.",
        )

    if shell_escape and not settings.allow_shell_escape:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Shell escape is disabled by server policy.",
        )

    task_timeout = min(timeout or settings.compile_timeout, settings.compile_timeout)
    encoded_payload = base64.b64encode(content).decode("utf-8")

    return CompileRequest(
        content=content,
        filename=filename,
        extension=extension,
        main_tex=main_tex,
        engine=engine,
        shell_escape=shell_escape,
        task_timeout=task_timeout,
        encoded_payload=encoded_payload,
    )


def _get_limiter(request: Request):
    return request.app.state.limiter


def rate_limit_route(route_func):
    @wraps(route_func)
    async def wrapper(*args, request: Request, **kwargs):
        limiter = _get_limiter(request)
        settings = request.app.state.settings
        decorated = limiter.limit(settings.rate_limit)(route_func)
        return await decorated(*args, **kwargs)

    return wrapper

    return wrapper


def _build_task_status_response(task_id: str, task: AsyncResult) -> TaskStatusResponse:
    data: dict[str, Any] = {
        "task_id": task_id,
        "state": task.state,
        "status": None,
        "pdf": None,
        "log": None,
        "errors": [],
        "detail": None,
    }

    if task.state == "SUCCESS":
        result = task.result or {}
        data.update(
            status=result.get("status"),
            pdf=result.get("pdf"),
            log=result.get("log"),
            errors=result.get("errors", []),
        )
    elif task.state in {"FAILURE", "REVOKED"}:
        data["detail"] = str(task.result) if task.result is not None else "Task failed."

    return TaskStatusResponse(**data)


@router.post("/compile", response_model=CompileResponse)
@rate_limit_route
async def compile_document(
    request: Request,
    compile_request: CompileRequest = Depends(validate_compile_request),
    api_key: str = Depends(api_key_auth),
) -> CompileResponse:
    try:
        task = compile_tex_task.apply_async(
            args=[
                compile_request.filename,
                compile_request.encoded_payload,
                compile_request.main_tex,
                compile_request.engine,
                compile_request.shell_escape,
                compile_request.task_timeout,
            ]
        )
        result_data = await asyncio.wait_for(
            asyncio.get_running_loop().run_in_executor(
                None, task.get, compile_request.task_timeout + 15
            ),
            timeout=compile_request.task_timeout + 15,
        )
    except CeleryError:
        logger.exception("Celery task failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Compilation failed while processing the request.",
        )
    except TimeoutError:
        logger.exception("Unhandled compilation error")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Compilation timed out or could not complete.",
        )
    except Exception:
        logger.exception("Unhandled compilation error")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Compilation timed out or could not complete.",
        )

    return CompileResponse(**result_data)


@router.post("/compile/async", response_model=TaskSubmissionResponse)
@rate_limit_route
async def submit_compile_job(
    request: Request,
    compile_request: CompileRequest = Depends(validate_compile_request),
    api_key: str = Depends(api_key_auth),
) -> TaskSubmissionResponse:
    task = compile_tex_task.apply_async(
        args=[
            compile_request.filename,
            compile_request.encoded_payload,
            compile_request.main_tex,
            compile_request.engine,
            compile_request.shell_escape,
            compile_request.task_timeout,
        ]
    )
    return TaskSubmissionResponse(task_id=task.id, state=task.state)


@router.get("/compile/{task_id}", response_model=TaskStatusResponse)
def get_compile_status(
    task_id: str,
    api_key: str = Depends(api_key_auth),
    settings: Settings = Depends(get_settings_dep),
) -> TaskStatusResponse:
    task = AsyncResult(task_id, app=celery)
    return _build_task_status_response(task_id, task)
