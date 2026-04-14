from __future__ import annotations

from latex_compile_service.config import get_settings, Settings


def get_settings_dep() -> Settings:
    return get_settings()
