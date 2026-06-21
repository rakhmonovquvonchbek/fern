from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from fern.config import DRAFTS_DIR, REPORT_PATH
from fern.drafts import service_slug


@dataclass
class ServiceEntry:
    name: str
    type: str = "unknown"
    status: str = "unknown"
    amount: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    cancel_email: str | None = None
    cancel_url: str | None = None
    source_date: str | None = None
    draft: str | None = None


@dataclass
class AuditData:
    generated: str | None = None
    total_services: int = 0
    active_trials: int = 0
    active_subscriptions: int = 0
    cancelled: int = 0
    unclear: int = 0
    monthly_spend: str | None = None
    sections: dict[str, list[ServiceEntry]] = field(default_factory=dict)


SECTION_KEYS = {
    "Trials Expiring Soon": "trials",
    "Active Subscriptions": "active",
    "Cancelled": "cancelled",
    "Unclear": "unclear",
}

FIELD_PATTERN = re.compile(r"^- \*\*(.+?):\*\* (.+)$")


def _load_drafts() -> dict[str, str]:
    drafts: dict[str, str] = {}
    if not DRAFTS_DIR.exists():
        return drafts
    for path in DRAFTS_DIR.glob("*_cancel.txt"):
        slug = path.stem.replace("_cancel", "")
        drafts[slug] = path.read_text()
    return drafts


def _match_draft(name: str, drafts: dict[str, str]) -> str | None:
    slug = service_slug(name)
    if slug in drafts:
        return drafts[slug]
    for key, content in drafts.items():
        if key in slug or slug in key:
            return content
    return None


def _parse_summary_line(line: str, data: AuditData) -> None:
    if "Total services found" in line:
        match = re.search(r":\*\* (\d+)", line)
        if match:
            data.total_services = int(match.group(1))
    elif "Active trials" in line:
        match = re.search(r":\*\* (\d+)", line)
        if match:
            data.active_trials = int(match.group(1))
    elif "Active subscriptions" in line:
        match = re.search(r":\*\* (\d+)", line)
        if match:
            data.active_subscriptions = int(match.group(1))
    elif line.startswith("- **Cancelled:**"):
        match = re.search(r":\*\* (\d+)", line)
        if match:
            data.cancelled = int(match.group(1))
    elif line.startswith("- **Unclear:**"):
        match = re.search(r":\*\* (\d+)", line)
        if match:
            data.unclear = int(match.group(1))
    elif "Estimated monthly spend" in line:
        match = re.search(r":\*\* (.+)$", line)
        if match:
            data.monthly_spend = match.group(1).strip()


def _parse_field(entry: ServiceEntry, label: str, value: str) -> None:
    value = value.strip()
    if value in ("Unknown", "_None found._"):
        value = None

    mapping = {
        "Type": "type",
        "Status": "status",
        "Amount": "amount",
        "Start date": "start_date",
        "End / renewal date": "end_date",
        "Cancel email": "cancel_email",
        "Cancel URL": "cancel_url",
        "Source email date": "source_date",
    }
    attr = mapping.get(label)
    if attr:
        setattr(entry, attr, value)


def parse_report(path: Path | None = None) -> AuditData:
    report_path = path or REPORT_PATH
    data = AuditData(sections={key: [] for key in SECTION_KEYS.values()})

    if not report_path.exists():
        return data

    drafts = _load_drafts()
    current_section: str | None = None
    current_entry: ServiceEntry | None = None
    in_summary = False

    def flush_entry() -> None:
        nonlocal current_entry
        if current_entry and current_section:
            data.sections[current_section].append(current_entry)
            current_entry = None

    for raw_line in report_path.read_text().splitlines():
        line = raw_line.strip()

        if line.startswith("Generated:"):
            data.generated = line.replace("Generated:", "").strip()
            continue

        if line == "## Summary":
            in_summary = True
            current_entry = None
            continue

        if in_summary:
            if line.startswith("## "):
                in_summary = False
            else:
                _parse_summary_line(line, data)
                continue

        if line.startswith("## "):
            flush_entry()
            heading = line[3:].strip()
            current_section = SECTION_KEYS.get(heading)
            continue

        if line.startswith("### "):
            flush_entry()
            name = line[4:].strip()
            current_entry = ServiceEntry(name=name, draft=_match_draft(name, drafts))
            continue

        if line == "_None found._":
            continue

        if current_entry:
            match = FIELD_PATTERN.match(line)
            if match:
                _parse_field(current_entry, match.group(1), match.group(2))

    flush_entry()

    return data


def _entry_to_dict(entry: ServiceEntry) -> dict:
    return {
        "name": entry.name,
        "type": entry.type,
        "status": entry.status,
        "amount": entry.amount,
        "start_date": entry.start_date,
        "end_date": entry.end_date,
        "cancel_email": entry.cancel_email,
        "cancel_url": entry.cancel_url,
        "source_date": entry.source_date,
        "draft": entry.draft,
    }


def audit_to_dict(data: AuditData) -> dict:
    return {
        "generated": data.generated,
        "total_services": data.total_services,
        "active_trials": data.active_trials,
        "active_subscriptions": data.active_subscriptions,
        "cancelled": data.cancelled,
        "unclear": data.unclear,
        "monthly_spend": data.monthly_spend,
        "sections": {
            key: [_entry_to_dict(e) for e in entries]
            for key, entries in data.sections.items()
        },
    }
