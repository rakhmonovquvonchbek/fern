from __future__ import annotations

import re
from datetime import date

from fern.config import DRAFTS_DIR
from fern.models import SubscriptionRecord


def service_slug(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^\w]+", "_", slug)
    slug = slug.strip("_")
    return slug or "unknown"


def _is_active_trial(record: SubscriptionRecord, today: date) -> bool:
    if record.type != "trial" or record.status == "cancelled":
        return False
    if record.end_date:
        try:
            end = date.fromisoformat(record.end_date[:10])
            return end >= today
        except ValueError:
            pass
    return record.status == "active"


def _needs_draft(record: SubscriptionRecord) -> bool:
    today = date.today()
    if record.status != "active":
        return False
    if record.type == "subscription":
        return True
    return _is_active_trial(record, today)


def _build_draft(record: SubscriptionRecord) -> str:
    lines: list[str] = []
    if record.cancel_url:
        lines.append(f"# Alternative: cancel online at {record.cancel_url}")
        lines.append("")

    cancel_to = record.cancel_email or "[find on service website]"
    kind = "free trial" if record.type == "trial" else "subscription"

    lines.extend(
        [
            f"To: {cancel_to}",
            f"Subject: Cancellation Request — {record.service_name}",
            "",
            f"Dear {record.service_name} Support,",
            "",
            f"Please cancel my {kind} effective immediately.",
            "Please confirm cancellation and that I will not be charged further.",
            "",
            "Thank you,",
            "[Your Name]",
            "",
        ]
    )
    return "\n".join(lines)


def write_drafts(records: list[SubscriptionRecord]) -> list[str]:
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    for record in records:
        if not _needs_draft(record):
            continue
        filename = f"{service_slug(record.service_name)}_cancel.txt"
        path = DRAFTS_DIR / filename
        path.write_text(_build_draft(record))
        written.append(str(path))

    return written
