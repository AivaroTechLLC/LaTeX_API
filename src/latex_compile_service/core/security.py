from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status
from latex_compile_service.config import get_settings, Settings


def get_settings_dep() -> Settings:
    return get_settings()


def api_key_auth(
    x_api_key: str = Header(..., alias="X-API-Key"),
    settings: Settings = Depends(get_settings_dep),
) -> str:
    if not x_api_key or x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
            headers={"WWW-Authenticate": "API key"},
        )
    return x_api_key


def virus_scan_stub(content: bytes) -> bool:
    # Placeholder for future antivirus/scan integration.
    return True
