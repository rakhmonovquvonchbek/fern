from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime

from bs4 import BeautifulSoup

from fern.config import BODY_TRUNCATE_BYTES


@dataclass
class ParsedEmail:
    message_id: str
    thread_id: str
    date: str
    date_iso: str
    sender: str
    subject: str
    body: str
    preview: str


def _header(headers: list[dict], name: str) -> str:
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            return header.get("value", "")
    return ""


def _decode_body(data: str) -> str:
    if not data:
        return ""
    padded = data + "=" * (-len(data) % 4)
    raw = base64.urlsafe_b64decode(padded.encode("utf-8"))
    return raw.decode("utf-8", errors="replace")


def _html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_parts(payload: dict) -> tuple[str, str]:
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data", "")

    plain = ""
    html = ""

    if mime_type == "text/plain" and body_data:
        plain = _decode_body(body_data)
    elif mime_type == "text/html" and body_data:
        html = _decode_body(body_data)

    for part in payload.get("parts", []):
        part_plain, part_html = _extract_parts(part)
        if part_plain and not plain:
            plain = part_plain
        if part_html and not html:
            html = part_html

    return plain, html


def _format_date(raw_date: str) -> tuple[str, str]:
    if not raw_date:
        return ("", "")
    try:
        dt = parsedate_to_datetime(raw_date)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
        return (dt.strftime("%Y-%m-%d"), dt.isoformat())
    except (TypeError, ValueError, OverflowError):
        return (raw_date[:10], raw_date)


def _truncate_body(text: str, max_bytes: int = BODY_TRUNCATE_BYTES) -> str:
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    truncated = encoded[:max_bytes].decode("utf-8", errors="ignore")
    return truncated.rstrip() + "..."


def parse_message(message: dict) -> ParsedEmail:
    payload = message.get("payload", {})
    headers = payload.get("headers", [])

    subject = _header(headers, "Subject")
    sender = _header(headers, "From")
    raw_date = _header(headers, "Date")
    date_str, date_iso = _format_date(raw_date)

    plain, html = _extract_parts(payload)
    body = plain.strip() if plain.strip() else _html_to_text(html)
    body = _truncate_body(body)

    preview = re.sub(r"\s+", " ", body).strip()
    if len(preview) > 200:
        preview = preview[:197] + "..."

    return ParsedEmail(
        message_id=message.get("id", ""),
        thread_id=message.get("threadId", ""),
        date=date_str,
        date_iso=date_iso,
        sender=sender,
        subject=subject,
        body=body,
        preview=preview,
    )
