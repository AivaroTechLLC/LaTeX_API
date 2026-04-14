import zipfile
from pathlib import Path

from latex_compile_service.services.compile_service import LatexCompiler
from latex_compile_service.utils.latex_utils import parse_latex_errors


def test_parse_latex_errors_simple():
    log = "! LaTeX Error: Something went wrong\nl.12 Some bad input"
    errors = parse_latex_errors(log)
    assert len(errors) >= 1
    assert any(entry.type == "error" for entry in errors)
    assert any("LaTeX Error" in entry.message for entry in errors)
    assert any(entry.line == 12 for entry in errors)


def test_parse_latex_errors_extended_patterns():
    log = (
        "Package foo Error: Something bad happened\n"
        "l.34 \\badcommand\n"
        "LaTeX Warning: Reference `fig:1` on page 3 undefined\n"
        "Undefined control sequence.\n"
        "./main.tex:42: Missing $ inserted\n"
        "Runaway argument?\n"
    )
    errors = parse_latex_errors(log)

    assert any(e.type == "error" and "Package foo Error" in e.message for e in errors)
    assert any(e.type == "warning" and "LaTeX Warning: Reference" in e.message for e in errors)
    assert any(e.type == "error" and e.file == "./main.tex" and e.line == 42 for e in errors)
    assert any(e.type == "error" and "Undefined control sequence" in e.message for e in errors)
    assert any(e.type == "error" and "Runaway argument" in e.message for e in errors)


def test_is_within_directory_safe():
    base = Path("/tmp/project").resolve()
    target = base / "subdir" / "file.tex"
    assert LatexCompiler._is_within_directory(base, target)


def test_is_within_directory_unsafe():
    base = Path("/tmp/project").resolve()
    target = Path("/tmp/project/../etc/passwd").resolve()
    assert not LatexCompiler._is_within_directory(base, target)


def test_zip_extraction_rejects_path_traversal(tmp_path):
    archive_path = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.writestr("../evil.txt", "malicious")

    compiler = LatexCompiler(settings=None)  # type: ignore[arg-type]
    try:
        compiler._extract_zip(archive_path, tmp_path)
        assert False, "Expected ValueError for illegal zip path"
    except ValueError as exc:
        assert "illegal file paths" in str(exc)


def test_resolve_engine_flag_defaults_to_pdf():
    compiler = LatexCompiler(settings=None)  # type: ignore[arg-type]
    assert compiler._resolve_engine_flag("pdflatex") == "-pdf"
    assert compiler._resolve_engine_flag("xelatex") == "-xelatex"
    assert compiler._resolve_engine_flag("lualatex") == "-lualatex"
    assert compiler._resolve_engine_flag("unknown") == "-pdf"
