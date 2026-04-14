import shutil
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

import redis.asyncio as aioredis
from latex_compile_service.app import app

client = TestClient(app)


def test_health_endpoint(monkeypatch):
    mock_client = MagicMock()
    mock_client.ping = AsyncMock(return_value=True)

    class AsyncContextManager:
        def __init__(self, obj):
            self.obj = obj

        async def __aenter__(self):
            return self.obj

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(aioredis, "from_url", lambda url: AsyncContextManager(mock_client))
    monkeypatch.setattr(shutil, "which", lambda path: "latexmk")

    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["redis"] == "ok"
    assert payload["latexmk"] == "ok"
    assert response.json()["status"] == "ok"


def test_compile_async_requires_api_key():
    response = client.post(
        "/api/v1/compile/async",
        files={"file": ("test.tex", b"\\documentclass{article}\\begin{document}Hello\\end{document}", "application/x-tex")},
    )
    assert response.status_code == 422


def test_compile_async_invalid_api_key():
    response = client.post(
        "/api/v1/compile/async",
        files={"file": ("test.tex", b"\\documentclass{article}\\begin{document}Hello\\end{document}", "application/x-tex")},
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 401


def test_compile_async_invalid_extension():
    response = client.post(
        "/api/v1/compile/async",
        files={"file": ("test.txt", b"hello world", "text/plain")},
        headers={"X-API-Key": "replace-with-secure-key"},
    )
    assert response.status_code == 400
    assert "Only .tex and .zip uploads are accepted" in response.text
