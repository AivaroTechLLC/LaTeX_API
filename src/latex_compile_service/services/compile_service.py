from __future__ import annotations

import base64
import shutil
import subprocess
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
                main_file = workspace_path / main_tex
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
            pdf_path = workspace_path / main_file.with_suffix(".pdf").name
            pdf_b64 = None
            if pdf_path.exists():
                pdf_b64 = base64.b64encode(pdf_path.read_bytes()).decode("utf-8")

            errors = parse_latex_errors(result["log"])
            status = "success" if pdf_b64 and result["returncode"] == 0 else "failure"

            return {
                "status": status,
                "pdf": pdf_b64,
                "log": result["log"],
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
            completed = subprocess.run(
                command,
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=timeout,
                preexec_fn=self._limit_resources,
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
            memory_limit = 512 * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit))
            resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
        except Exception:
            pass

    def _extract_zip(self, archive_path: Path, destination: Path) -> None:
        with zipfile.ZipFile(archive_path, "r") as archive:
            for member in archive.namelist():
                target_path = destination / member
                if not self._is_within_directory(destination, target_path):
                    raise ValueError("ZIP archive contains illegal file paths.")
            archive.extractall(destination)

    @staticmethod
    def _is_within_directory(directory: Path, target: Path) -> bool:
        try:
            return directory.resolve() in target.resolve().parents or directory.resolve() == target.resolve()
        except RuntimeError:
            return False
