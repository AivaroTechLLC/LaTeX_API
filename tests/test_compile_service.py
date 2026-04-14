from __future__ import annotations

import base64
import io
import subprocess
import zipfile
from pathlib import Path

import pytest

from latex_compile_service.services.compile_service import LatexCompiler


class DummySettings:
    latexmk_binary = "latexmk"
    compile_timeout = 120


def test_run_latexmk_missing_binary_returns_failure(monkeypatch):
    compiler = LatexCompiler(settings=DummySettings())

    def fake_run(*args, **kwargs):
        raise FileNotFoundError("[Errno 2] No such file or directory: 'latexmk'")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = compiler._run_latexmk(Path("."), Path("dummy.tex"), "pdflatex", False, 10)
    assert result["returncode"] == 1
    assert "latexmk binary not found" in result["log"]


def test_run_latexmk_timeout_returns_failure(monkeypatch):
    compiler = LatexCompiler(settings=DummySettings())

    class TimeoutExc(subprocess.TimeoutExpired):
        def __init__(self):
            super().__init__(cmd="latexmk", timeout=1, output="", stderr="timeout")

    def fake_run(*args, **kwargs):
        raise TimeoutExc()

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = compiler._run_latexmk(Path("."), Path("dummy.tex"), "pdflatex", False, 1)
    assert result["returncode"] == 1
    assert "Compilation timed out" in result["log"]


def test_compile_source_bytes_calls_run_latexmk_and_returns_pdf(tmp_path, monkeypatch):
    settings = DummySettings()
    compiler = LatexCompiler(settings=settings)
    source = b"\\documentclass{article}\\begin{document}Hello\\end{document}"

    def fake_run_latexmk(workspace, main_file, engine, shell_escape, timeout):
        pdf_path = workspace / main_file.with_suffix(".pdf").name
        pdf_path.write_bytes(b"PDFDATA")
        return {"returncode": 0, "log": "Compilation complete"}

    monkeypatch.setattr(compiler, "_run_latexmk", fake_run_latexmk)

    result = compiler.compile_source_bytes(
        filename="hello.tex",
        content=source,
        main_tex=None,
        engine="pdflatex",
        shell_escape=False,
        timeout=10,
    )

    assert result["status"] == "success"
    assert result["pdf"] == base64.b64encode(b"PDFDATA").decode("utf-8")
    assert "Compilation complete" in result["log"]


def test_compile_source_bytes_rejects_escaped_main_tex(monkeypatch):
    settings = DummySettings()
    compiler = LatexCompiler(settings=settings)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w") as archive:
        archive.writestr("valid.tex", "\\documentclass{article}\\begin{document}Hello\\end{document}")
    zip_bytes = buf.getvalue()

    with pytest.raises(ValueError, match=r"main_tex path '../escape.tex' escapes the project workspace"):
        compiler.compile_source_bytes(
            filename="project.zip",
            content=zip_bytes,
            main_tex="../escape.tex",
            engine="pdflatex",
            shell_escape=False,
            timeout=10,
        )
