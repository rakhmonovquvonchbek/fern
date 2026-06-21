from __future__ import annotations

import json
import re
import time
from pathlib import Path

import anthropic

from fern.config import ANTHROPIC_MODEL, CACHE_DIR, get_anthropic_api_key
from fern.gmail.parse import ParsedEmail
from fern.models import SubscriptionRecord

BATCH_SIZE = 10
BATCH_SLEEP_SECONDS = 1

EXTRACTION_PROMPT = """You analyze emails to extract subscription and free trial information.

For each email, return a JSON object with these fields:
- service_name (string, required)
- type: "trial" | "subscription" | "unclear"
- amount (string or null, e.g. "$9.99/mo")
- start_date (ISO date YYYY-MM-DD or null)
- end_date (ISO date YYYY-MM-DD or null — trial end or next renewal)
- status: "active" | "expired" | "cancelled" | "unclear"
- cancel_email (string or null)
- cancel_url (string or null)
- confidence (number 0-1)
- message_id (string, must match the email's message_id)

Use each email's date as context for whether trials are still active or expired.
If an email confirms cancellation, status is "cancelled".
If unclear, use "unclear" rather than guessing.

Return ONLY a JSON array of objects, one per email, in the same order as provided."""


def _cache_path(message_id: str) -> Path:
    safe_id = re.sub(r"[^\w\-]", "_", message_id)
    return CACHE_DIR / f"{safe_id}.json"


def load_cached_record(message_id: str) -> SubscriptionRecord | None:
    path = _cache_path(message_id)
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return SubscriptionRecord.from_dict(data)


def save_cached_record(record: SubscriptionRecord) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(record.source_message_id)
    path.write_text(json.dumps(record.to_dict(), indent=2))


def _parse_json_response(text: str):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _format_email_for_batch(index: int, email: ParsedEmail) -> str:
    return (
        f"--- Email {index} ---\n"
        f"message_id: {email.message_id}\n"
        f"date: {email.date}\n"
        f"from: {email.sender}\n"
        f"subject: {email.subject}\n"
        f"body:\n{email.body}\n"
    )


def _record_from_extraction(data: dict, email: ParsedEmail) -> SubscriptionRecord | None:
    try:
        return SubscriptionRecord.from_dict(
            {
                **data,
                "source_message_id": email.message_id,
                "source_date": email.date,
            }
        )
    except (TypeError, ValueError):
        return None


def extract_batch_local(
    emails: list[ParsedEmail],
    *,
    client: anthropic.Anthropic,
    use_cache: bool = True,
) -> list[SubscriptionRecord]:
    if not emails:
        return []

    user_content = "Extract subscription info from these emails:\n\n"
    user_content += "\n".join(_format_email_for_batch(i + 1, e) for i, e in enumerate(emails))

    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=4096,
        system=EXTRACTION_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    text_blocks = [block.text for block in response.content if block.type == "text"]
    if not text_blocks:
        return []

    try:
        parsed = _parse_json_response(text_blocks[0])
    except json.JSONDecodeError:
        return []

    if isinstance(parsed, dict):
        parsed = [parsed]
    if not isinstance(parsed, list):
        return []

    records: list[SubscriptionRecord] = []
    for index, email in enumerate(emails):
        if index >= len(parsed):
            break
        item = parsed[index]
        if not isinstance(item, dict):
            continue
        record = _record_from_extraction(item, email)
        if record is None:
            continue
        if use_cache:
            save_cached_record(record)
        records.append(record)

    return records


def extract_all(
    emails: list[ParsedEmail],
    *,
    use_cache: bool = True,
    verbose: bool = False,
) -> list[SubscriptionRecord]:
    client = anthropic.Anthropic(api_key=get_anthropic_api_key())
    records: list[SubscriptionRecord] = []
    pending: list[ParsedEmail] = []

    for email in emails:
        if use_cache:
            cached = load_cached_record(email.message_id)
            if cached is not None:
                records.append(cached)
                continue
        pending.append(email)

    total_batches = (len(pending) + BATCH_SIZE - 1) // BATCH_SIZE if pending else 0

    for batch_index in range(0, len(pending), BATCH_SIZE):
        batch = pending[batch_index : batch_index + BATCH_SIZE]
        batch_num = batch_index // BATCH_SIZE + 1

        if verbose:
            print(f"Extracting batch {batch_num}/{total_batches} ({len(batch)} email(s))")

        batch_records = extract_batch_local(batch, client=client, use_cache=use_cache)
        records.extend(batch_records)

        if verbose and len(batch_records) < len(batch):
            print(f"  Extracted {len(batch_records)}/{len(batch)} from batch")

        if batch_index + BATCH_SIZE < len(pending):
            time.sleep(BATCH_SLEEP_SECONDS)

    return records


def load_all_cached_records() -> list[SubscriptionRecord]:
    if not CACHE_DIR.exists():
        return []
    records: list[SubscriptionRecord] = []
    for path in sorted(CACHE_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text())
            records.append(SubscriptionRecord.from_dict(data))
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
    return records
