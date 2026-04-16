from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from latex_compile_service.config import get_settings


def get_client_ip(request: Request, trusted_proxies: set[str] | None = None) -> str:
    if trusted_proxies is None:
        trusted_proxies = set(get_settings().trusted_proxy_ips)

    client_host = request.client.host if request.client is not None else None
    if client_host and client_host in trusted_proxies:
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

    return client_host or get_remote_address(request)


limiter = Limiter(key_func=get_client_ip)
