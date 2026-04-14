from fastapi.testclient import TestClient

from latex_compile_service.app import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
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
