from __future__ import annotations

import re
from datetime import date, datetime

from fern.models import SubscriptionRecord

MAX_DATE = date.max


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_monthly_amount(amount: str | None) -> float | None:
    if not amount:
        return None
    match = re.search(r"[\$€£]?\s*([\d,]+(?:\.\d{2})?)", amount)
    if not match:
        return None
    value = float(match.group(1).replace(",", ""))
    lower = amount.lower()
    if "/yr" in lower or "year" in lower or "annual" in lower:
        return round(value / 12, 2)
    return value


def _format_entry(record: SubscriptionRecord) -> str:
    lines = [
        f"### {record.service_name}",
        "",
        f"- **Type:** {record.type}",
        f"- **Status:** {record.status}",
        f"- **Amount:** {record.amount or 'Unknown'}",
        f"- **Start date:** {record.start_date or 'Unknown'}",
        f"- **End / renewal date:** {record.end_date or 'Unknown'}",
    ]
    if record.cancel_email:
        lines.append(f"- **Cancel email:** {record.cancel_email}")
    if record.cancel_url:
        lines.append(f"- **Cancel URL:** {record.cancel_url}")
    lines.append(f"- **Source email date:** {record.source_date}")
    lines.append("")
    return "\n".join(lines)


def _is_active_trial(record: SubscriptionRecord, today: date) -> bool:
    if record.type != "trial" or record.status == "cancelled":
        return False
    end = _parse_date(record.end_date)
    if end is not None:
        return end >= today
    return record.status == "active"


def _is_active_subscription(record: SubscriptionRecord) -> bool:
    return record.type == "subscription" and record.status == "active"


def write_report(records: list[SubscriptionRecord], path) -> None:
    today = date.today()

    trials = [r for r in records if _is_active_trial(r, today)]
    trials.sort(key=lambda r: _parse_date(r.end_date) or MAX_DATE)

    active_subs = [r for r in records if _is_active_subscription(r)]
    active_subs.sort(key=lambda r: r.service_name.lower())

    cancelled = [r for r in records if r.status == "cancelled"]
    cancelled.sort(
        key=lambda r: _parse_date(r.source_date) or date.min,
        reverse=True,
    )

    classified = {id(r) for r in trials + active_subs + cancelled}
    unclear = [r for r in records if id(r) not in classified]
    unclear.sort(key=lambda r: r.service_name.lower())

    monthly_total = sum(
        amt
        for r in active_subs
        if (amt := _parse_monthly_amount(r.amount)) is not None
    )

    lines = [
        "# Fern Subscription Audit",
        "",
        f"Generated: {today.isoformat()}",
        "",
        "## Summary",
        "",
        f"- **Total services found:** {len(records)}",
        f"- **Active trials:** {len(trials)}",
        f"- **Active subscriptions:** {len(active_subs)}",
        f"- **Cancelled:** {len(cancelled)}",
        f"- **Unclear:** {len(unclear)}",
    ]
    if monthly_total > 0:
        lines.append(f"- **Estimated monthly spend:** ${monthly_total:.2f}")
    lines.append("")

    sections = [
        ("Trials Expiring Soon", trials),
        ("Active Subscriptions", active_subs),
        ("Cancelled", cancelled),
        ("Unclear", unclear),
    ]

    for title, section_records in sections:
        lines.append(f"## {title}")
        lines.append("")
        if not section_records:
            lines.append("_None found._")
            lines.append("")
            continue
        for record in section_records:
            lines.extend(_format_entry(record).splitlines())

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))
