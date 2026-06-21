from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from typing import Any

from fern.config import CONFIG_PATH, DEFAULT_API_URL, ensure_fern_home


@dataclass
class FernSettings:
    install_id: str
    telemetry: bool = False
    telemetry_asked: bool = False
    api_url: str = DEFAULT_API_URL
    audit_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FernSettings:
        return cls(
            install_id=str(data.get("install_id") or uuid.uuid4()),
            telemetry=bool(data.get("telemetry", False)),
            telemetry_asked=bool(data.get("telemetry_asked", False)),
            api_url=str(data.get("api_url") or DEFAULT_API_URL),
            audit_count=int(data.get("audit_count", 0)),
        )


def load_settings() -> FernSettings:
    ensure_fern_home()
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text())
            return FernSettings.from_dict(data)
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    settings = FernSettings(install_id=str(uuid.uuid4()))
    save_settings(settings)
    return settings


def save_settings(settings: FernSettings) -> None:
    ensure_fern_home()
    CONFIG_PATH.write_text(json.dumps(settings.to_dict(), indent=2))


def get_install_id() -> str:
    return load_settings().install_id


def get_api_url() -> str:
    settings = load_settings()
    return settings.api_url or DEFAULT_API_URL


def increment_audit_count() -> int:
    settings = load_settings()
    settings.audit_count += 1
    save_settings(settings)
    return settings.audit_count
