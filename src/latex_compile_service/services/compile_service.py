from __future__ import annotations

import base64
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from latex_compile_service.config import Settings
from latex_compile_service.utils.latex_utils import parse_latex_errors


class LatexCompiler:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def compile_source_bytes(
        self,
        filename: str,
        content: bytes,
        main_tex: str | None,
        engine: str,
        shell_escape: bool,
        timeout: int,
    ) -> dict[str, Any]:
        with tempfile.TemporaryDirectory(prefix="latex_project_") as workspace:
            workspace_path = Path(workspace)
            archive_path = workspace_path / filename
            archive_path.write_bytes(content)

            if archive_path.suffix.lower() == ".zip":
                self._extract_zip(archive_path, workspace_path)
                archive_path.unlink(missing_ok=True)
                if not main_tex:
                    raise ValueError("main_tex is required for ZIP projects.")
                main_file = self._validate_main_tex_path(workspace_path, main_tex)
            else:
                main_file = archive_path

            if not main_file.exists():
                raise ValueError(f"Main TeX file not found: {main_file.name}")

            result = self._run_latexmk(
                workspace=workspace_path,
                main_file=main_file,
                engine=engine,
                shell_escape=shell_escape,
                timeout=timeout,
            )
            pdf_path = main_file.parent / main_file.with_suffix(".pdf").name
            pdf_b64 = None
            if pdf_path.exists():
                pdf_b64 = base64.b64encode(pdf_path.read_bytes()).decode("utf-8")

            log = result["log"]
            if len(log) > self.settings.max_log_chars:
                log = log[-self.settings.max_log_chars:]
                log = f"[log truncated to last {self.settings.max_log_chars} chars]\n" + log
            errors = parse_latex_errors(log)
            status = "success" if pdf_b64 and result["returncode"] == 0 else "failure"

            return {
                "status": status,
                "pdf": pdf_b64,
                "log": log,
                "errors": errors,
            }

    def _run_latexmk(
        self,
        workspace: Path,
        main_file: Path,
        engine: str,
        shell_escape: bool,
        timeout: int,
    ) -> dict[str, Any]:
        engine_flag = self._resolve_engine_flag(engine)
        relative_main_file = main_file.relative_to(workspace)
        command = [
            self.settings.latexmk_binary,
            engine_flag,
            "-interaction=nonstopmode",
            "-file-line-error",
            "-halt-on-error",
            "-f",
            "-cd",
            str(relative_main_file),
        ]
        if shell_escape:
            command.append("-shell-escape")

        try:
            kwargs: dict[str, Any] = {}
            if sys.platform != "win32":
                kwargs["preexec_fn"] = self._limit_resources

            completed = subprocess.run(
                command,
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=timeout,
                **kwargs,
            )
            log_output = completed.stdout + "\n" + completed.stderr
            return {
                "returncode": completed.returncode,
                "log": log_output,
            }
        except FileNotFoundError as exc:
            return {
                "returncode": 1,
                "log": f"latexmk binary not found: {exc}",
            }
        except subprocess.TimeoutExpired as exc:
            return {
                "returncode": 1,
                "log": f"Compilation timed out after {timeout} seconds.\n{exc.stdout or ''}\n{exc.stderr or ''}",
            }

    def _resolve_engine_flag(self, engine: str) -> str:
        mapping = {
            "pdflatex": "-pdf",
            "xelatex": "-xelatex",
            "lualatex": "-lualatex",
        }
        return mapping.get(engine, "-pdf")

    def _limit_resources(self) -> None:
        try:
            import resource

            cpu_limit = min(self.settings.compile_timeout, 120)
            memory_limit = self.settings.max_memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit))
            resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
        except Exception:
            pass

    @staticmethod
    def _validate_main_tex_path(workspace: Path, main_tex: str) -> Path:
        candidate = (workspace / main_tex).resolve()
        workspace_resolved = workspace.resolve()
        if workspace_resolved not in candidate.parents and candidate != workspace_resolved:
            raise ValueError(
                f"main_tex path '{main_tex}' escapes the project workspace."
            )
        if candidate.suffix.lower() != ".tex":
            raise ValueError(
                f"main_tex must reference a .tex file, got: '{main_tex}'"
            )
        return candidate

    def _extract_zip(self, archive_path: Path, destination: Path) -> None:
        with zipfile.ZipFile(archive_path, "r") as archive:
            for member in archive.namelist():
                target_path = destination / member
                if not self._is_within_directory(destination, target_path):
                    raise ValueError("ZIP archive contains illegal file paths.")
            archive.extractall(destination)

        destination_resolved = destination.resolve()
        for root, dirs, files in os.walk(destination, topdown=True):
            for name in dirs + files:
                path = Path(root) / name
                try:
                    resolved = path.resolve()
                except OSError:
                    raise ValueError("ZIP archive contains illegal file paths.")
                if destination_resolved not in resolved.parents and resolved != destination_resolved:
                    raise ValueError("ZIP archive contains illegal file paths.")

    @staticmethod
    def _is_within_directory(directory: Path, target: Path) -> bool:
        try:
            return directory.resolve() in target.resolve().parents or directory.resolve() == target.resolve()
        except RuntimeError:
            return False
