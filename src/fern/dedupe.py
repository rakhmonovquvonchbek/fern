from __future__ import annotations

import re
from datetime import date, datetime

from fern.models import RecordStatus, SubscriptionRecord

_SUFFIXES = {"inc", "llc", "ltd", "corp", "co", "company"}


def normalize_service_name(name: str) -> str:
    cleaned = name.lower().strip()
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)
    tokens = [t for t in cleaned.split() if t and t not in _SUFFIXES]
    return " ".join(tokens) or cleaned


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _status_priority(status: RecordStatus) -> int:
    order = {"active": 4, "expired": 2, "cancelled": 3, "unclear": 1}
    return order.get(status, 0)


def _pick_best(records: list[SubscriptionRecord]) -> SubscriptionRecord:
    today = date.today()

    def sort_key(record: SubscriptionRecord) -> tuple:
        source_date = _parse_date(record.source_date) or date.min
        end_date = _parse_date(record.end_date)
        future_trial = (
            record.type == "trial"
            and end_date is not None
            and end_date >= today
            and record.status != "cancelled"
        )
        return (
            source_date.toordinal(),
            _status_priority(record.status),
            1 if future_trial else 0,
            record.confidence,
        )

    return max(records, key=sort_key)


def dedupe_records(records: list[SubscriptionRecord]) -> list[SubscriptionRecord]:
    groups: dict[str, list[SubscriptionRecord]] = {}
    for record in records:
        key = normalize_service_name(record.service_name)
        groups.setdefault(key, []).append(record)

    deduped: list[SubscriptionRecord] = []
    for group in groups.values():
        deduped.append(_pick_best(group))

    return deduped
