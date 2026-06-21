from __future__ import annotations

import shutil
from pathlib import Path

from fern.config import (
    CACHE_DIR,
    CREDENTIALS_PATH,
    DRAFTS_DIR,
    ENV_PATH,
    FERN_HOME,
    LEGACY_FERN_HOME,
    MIGRATION_FLAG,
    OUTPUT_DIR,
    REPORT_PATH,
    TOKEN_PATH,
    ensure_fern_home,
)


def _copy_if_missing(src: Path, dst: Path) -> bool:
    if not src.exists() or dst.exists():
        return False
    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    return True


def _merge_output_dir(src: Path, dst: Path) -> bool:
    if not src.exists():
        return False
    copied = False
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.rglob("*"):
        if not item.is_file():
            continue
        rel = item.relative_to(src)
        target = dst / rel
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)
            copied = True
    return copied


def migrate_legacy_config() -> bool:
    """Migrate v0.1 config from ~/fern to ~/.fern. Returns True if anything moved."""
    ensure_fern_home()
    if MIGRATION_FLAG.exists():
        return False

    migrated = False
    legacy = LEGACY_FERN_HOME

    if _copy_if_missing(legacy / "credentials.json", CREDENTIALS_PATH):
        migrated = True
    if _copy_if_missing(legacy / "token.json", TOKEN_PATH):
        migrated = True
    if _copy_if_missing(legacy / ".env", ENV_PATH):
        migrated = True
    if _merge_output_dir(legacy / "output", OUTPUT_DIR):
        migrated = True

    MIGRATION_FLAG.write_text("done\n")
    if migrated:
        print("Migrated v0.1 config from ~/fern to ~/.fern")
    return migrated
