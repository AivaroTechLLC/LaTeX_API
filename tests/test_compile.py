import base64
from pathlib import Path
from unittest.mock import MagicMock

from celery.result import AsyncResult


def test_compile_async_returns_task_id(client, monkeypatch, tmp_path):
    fake_task = MagicMock()
    fake_task.id = "fake-task-id"
    fake_task.state = "PENDING"

    def fake_apply_async(*args, **kwargs):
        return fake_task

    from latex_compile_service.api.routers.compile import compile_tex_task

    monkeypatch.setattr(compile_tex_task, "apply_async", fake_apply_async)

    tex_path = tmp_path / "hello.tex"
    tex_path.write_bytes(b"\\documentclass{article}\\begin{document}Hello world\\end{document}")

    with tex_path.open("rb") as tex_file:
        response = client.post(
            "/api/v1/compile/async",
            files={"file": ("hello.tex", tex_file, "application/x-tex")},
            headers={"X-API-Key": "replace-with-secure-key"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["task_id"] == "fake-task-id"
    assert payload["state"] == "PENDING"


def test_compile_status_returns_task_state(client, monkeypatch):
    fake_result = MagicMock(spec=AsyncResult)
    fake_result.state = "SUCCESS"
    fake_result.result = {
        "status": "success",
        "pdf": base64.b64encode(b"PDFDATA").decode("utf-8"),
        "log": "Compilation completed",
        "errors": [],
    }

    def fake_async_result(task_id, app=None):
        assert task_id == "fake-task-id"
        return fake_result

    from latex_compile_service.api.routers import compile as compile_router_module

    monkeypatch.setattr(compile_router_module, "AsyncResult", fake_async_result)

    response = client.get(
        "/api/v1/compile/fake-task-id",
        headers={"X-API-Key": "replace-with-secure-key"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["task_id"] == "fake-task-id"
    assert payload["state"] == "SUCCESS"
    assert payload["status"] == "success"
    assert payload["pdf"] is not None
