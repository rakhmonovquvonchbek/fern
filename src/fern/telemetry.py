from __future__ import annotations

import platform

import httpx

from fern.config import USER_AGENT
from fern.settings import get_api_url, get_install_id, load_settings


def ask_telemetry_opt_in() -> None:
    settings = load_settings()
    if settings.telemetry_asked:
        return

    try:
        answer = input(
            "Can Fern send anonymous usage stats (audit count, OS) "
            "to help improve the tool? No personal data ever. [y/N] "
        ).strip().lower()
    except (EOFError, KeyboardInterrupt):
        answer = "n"

    settings.telemetry = answer in ("y", "yes")
    settings.telemetry_asked = True
    from fern.settings import save_settings

    save_settings(settings)


def send_ping() -> None:
    settings = load_settings()
    if not settings.telemetry:
        return

    api_url = get_api_url()
    if not api_url:
        return

    payload = {
        "install_id": settings.install_id,
        "os": platform.system().lower(),
        "audit_count": settings.audit_count,
    }
    try:
        httpx.post(
            f"{api_url.rstrip('/')}/ping",
            json=payload,
            headers={
                "User-Agent": USER_AGENT,
                "X-Fern-Install-ID": settings.install_id,
            },
            timeout=10.0,
        )
    except httpx.HTTPError:
        pass
