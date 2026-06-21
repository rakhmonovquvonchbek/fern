from __future__ import annotations

import json
import os
import re
from datetime import date

import anthropic

ANTHROPIC_MODEL = "claude-sonnet-4-6"

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


def _parse_json_response(text: str):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _format_email(index: int, email: dict) -> str:
    return (
        f"--- Email {index} ---\n"
        f"message_id: {email['message_id']}\n"
        f"date: {email['date']}\n"
        f"from: {email['sender']}\n"
        f"subject: {email['subject']}\n"
        f"body:\n{email['body']}\n"
    )


def extract_records(emails: list[dict]) -> list[dict]:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    user_content = "Extract subscription info from these emails:\n\n"
    user_content += "\n".join(_format_email(i + 1, e) for i, e in enumerate(emails))

    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=4096,
        system=EXTRACTION_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    text_blocks = [b.text for b in response.content if b.type == "text"]
    if not text_blocks:
        return []

    parsed = _parse_json_response(text_blocks[0])
    if isinstance(parsed, dict):
        parsed = [parsed]

    records = []
    for index, email in enumerate(emails):
        if index >= len(parsed):
            break
        item = parsed[index]
        if not isinstance(item, dict):
            continue
        records.append(
            {
                "service_name": str(item.get("service_name", "Unknown")),
                "type": item.get("type", "unclear"),
                "amount": item.get("amount"),
                "start_date": item.get("start_date"),
                "end_date": item.get("end_date"),
                "status": item.get("status", "unclear"),
                "cancel_email": item.get("cancel_email"),
                "cancel_url": item.get("cancel_url"),
                "source_message_id": email["message_id"],
                "source_date": email["date"],
                "confidence": float(item.get("confidence", 0.0)),
            }
        )
    return records
