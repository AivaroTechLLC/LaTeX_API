from __future__ import annotations

from pydantic import BaseModel, Field


class CompileResponse(BaseModel):
    status: str = Field(..., description="Compilation status: success or failure")
    pdf: str | None = Field(None, description="Base64-encoded PDF content if compilation succeeds")
    log: str = Field(..., description="Raw latexmk log output")
    errors: list[str] = Field(default_factory=list, description="Parsed LaTeX errors and warnings")


class TaskSubmissionResponse(BaseModel):
    task_id: str = Field(..., description="Celery task id for the submitted compilation job")
    state: str = Field(..., description="Current Celery task state")


class TaskStatusResponse(BaseModel):
    task_id: str = Field(..., description="Celery task id")
    state: str = Field(..., description="Current Celery task state")
    status: str | None = Field(None, description="Compilation status if the task is complete")
    pdf: str | None = Field(None, description="Base64-encoded PDF content if compilation succeeded")
    log: str | None = Field(None, description="Raw latexmk log output returned by the task")
    errors: list[str] = Field(default_factory=list, description="Parsed LaTeX errors and warnings if available")
    detail: str | None = Field(None, description="Optional failure detail for task errors")
