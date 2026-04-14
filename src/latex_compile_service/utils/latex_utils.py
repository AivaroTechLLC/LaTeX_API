from __future__ import annotations

import re


def parse_latex_errors(log: str) -> list[str]:
    errors: list[str] = []
    for line in log.splitlines():
        text = line.strip()
        if not text:
            continue
        if text.startswith("!") or text.startswith("l."):
            errors.append(text)

    if not errors:
        errors.extend(re.findall(r"! LaTeX Error:.*", log))

    return errors[:25]
