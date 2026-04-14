from __future__ import annotations

import re


def parse_latex_errors(log: str) -> list[dict]:
    errors: list[dict] = []
    previous_error: dict | None = None

    file_line_re = re.compile(r"^(?P<file>.+?):(?P<line>\d+):\s*(?P<message>.+)$")
    latex_error_re = re.compile(r"^!\s*(?P<message>LaTeX Error: .+)$")
    package_error_re = re.compile(r"^(?:!\s*)?(?P<message>Package [^:]+ Error: .+)$")
    warning_ref_re = re.compile(r"^LaTeX Warning: (Reference|Citation) .+")
    undefined_control_re = re.compile(r"^Undefined control sequence(?:\.|$).*")
    missing_re = re.compile(r"^(Missing \$ inserted|Runaway argument\?).*")
    line_context_re = re.compile(r"^l\.(?P<line>\d+)\s*(?P<message>.*)$")

    def add_error(
        message: str,
        type_: str = "error",
        line: int | None = None,
        file: str | None = None,
    ) -> dict:
        error = {
            "type": type_,
            "message": message.strip(),
            "line": line,
            "file": file,
        }
        errors.append(error)
        return error

    for line in log.splitlines():
        text = line.strip()
        if not text:
            continue

        file_match = file_line_re.match(text)
        if file_match:
            add_error(
                message=file_match.group("message"),
                type_="error",
                line=int(file_match.group("line")),
                file=file_match.group("file"),
            )
            previous_error = errors[-1]
            continue

        latex_match = latex_error_re.match(text)
        package_match = package_error_re.match(text)
        warning_match = warning_ref_re.match(text)
        undefined_match = undefined_control_re.match(text)
        missing_match = missing_re.match(text)
        line_context_match = line_context_re.match(text)

        if latex_match:
            previous_error = add_error(message=latex_match.group("message"), type_="error")
            continue

        if package_match:
            previous_error = add_error(message=package_match.group("message"), type_="error")
            continue

        if warning_match:
            previous_error = add_error(message=text, type_="warning")
            continue

        if undefined_match:
            previous_error = add_error(message=text, type_="error")
            continue

        if missing_match:
            previous_error = add_error(message=text, type_="error")
            continue

        if line_context_match and previous_error is not None:
            if previous_error["line"] is None:
                previous_error["line"] = int(line_context_match.group("line"))
            message_suffix = line_context_match.group("message").strip()
            if message_suffix:
                previous_error["message"] = f"{previous_error['message']} {message_suffix}".strip()
            continue

        if text.startswith("!"):
            previous_error = add_error(message=text.lstrip("! "), type_="error")
            continue

    if not errors:
        for message in re.findall(r"! LaTeX Error:.*", log):
            add_error(message=message, type_="error")

    return errors[:25]
