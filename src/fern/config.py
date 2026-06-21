import os
from pathlib import Path

from dotenv import load_dotenv

FERN_HOME = Path.home() / ".fern"
CREDENTIALS_PATH = FERN_HOME / "credentials.json"
TOKEN_PATH = FERN_HOME / "token.json"
ENV_PATH = FERN_HOME / ".env"
CONFIG_PATH = FERN_HOME / "config.json"
OUTPUT_DIR = FERN_HOME / "output"
REPORT_PATH = OUTPUT_DIR / "report.md"
DRAFTS_DIR = OUTPUT_DIR / "drafts"
CACHE_DIR = OUTPUT_DIR / "cache"
MIGRATION_FLAG = FERN_HOME / ".migration_done"

LEGACY_FERN_HOME = Path.home() / "fern"

GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
SCOPES = [GMAIL_READONLY_SCOPE]

ANTHROPIC_MODEL = "claude-sonnet-4-6"
USER_AGENT = "Fern/0.2"
DEFAULT_MONTHS = 6
BODY_TRUNCATE_BYTES = 8192
PREVIEW_CHARS = 200

DEFAULT_API_URL = ""  # Set after Cloud Run deploy; override in config.json


def ensure_fern_home() -> None:
    FERN_HOME.mkdir(parents=True, exist_ok=True)
    ensure_output_dirs()


def ensure_output_dirs() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def reload_env() -> None:
    if ENV_PATH.exists():
        load_dotenv(ENV_PATH, override=True)


reload_env()


def get_anthropic_api_key_optional() -> str | None:
    reload_env()
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    return key or None


def get_anthropic_api_key() -> str:
    key = get_anthropic_api_key_optional()
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Add your key to ~/.fern/.env for "
            "unlimited audits:\n  ANTHROPIC_API_KEY=sk-ant-...\n"
            "Get one free at https://console.anthropic.com"
        )
    return key
