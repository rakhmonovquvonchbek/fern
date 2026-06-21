from __future__ import annotations

import httpx

from fern.config import USER_AGENT
from fern.extractor.claude import BATCH_SIZE, BATCH_SLEEP_SECONDS
from fern.gmail.parse import ParsedEmail
from fern.models import SubscriptionRecord
from fern.settings import get_api_url, get_install_id


class FreeLimitReached(Exception):
    def __init__(self, message: str, error_code: str = "free_limit_reached"):
        super().__init__(message)
        self.error_code = error_code


def extract_batch_api(
    emails: list[ParsedEmail],
    *,
    client: httpx.Client | None = None,
) -> list[SubscriptionRecord]:
    if not emails:
        return []

    api_url = get_api_url()
    if not api_url:
        raise RuntimeError(
            "No API URL configured. Add ANTHROPIC_API_KEY to ~/.fern/.env for "
            "unlimited local audits, or set api_url in ~/.fern/config.json."
        )

    payload = {
        "emails": [
            {
                "message_id": e.message_id,
                "subject": e.subject,
                "sender": e.sender,
                "date": e.date,
                "body": e.body,
            }
            for e in emails
        ]
    }

    owns_client = client is None
    if client is None:
        client = httpx.Client(timeout=120.0)

    try:
        response = client.post(
            f"{api_url.rstrip('/')}/extract",
            json=payload,
            headers={
                "User-Agent": USER_AGENT,
                "X-Fern-Install-ID": get_install_id(),
                "Content-Type": "application/json",
            },
        )
    finally:
        if owns_client:
            client.close()

    if response.status_code == 429:
        data = response.json()
        raise FreeLimitReached(
            data.get("message", "Free audit limit reached."),
            data.get("error", "free_limit_reached"),
        )

    response.raise_for_status()
    records: list[SubscriptionRecord] = []
    for item in response.json().get("records", []):
        records.append(SubscriptionRecord.from_dict(item))
    return records


def extract_all_routed(
    emails: list[ParsedEmail],
    *,
    use_cache: bool = True,
    verbose: bool = False,
    use_local_key: bool | None = None,
) -> list[SubscriptionRecord]:
    from fern.config import get_anthropic_api_key_optional
    from fern.extractor.claude import extract_all as extract_all_local
    from fern.extractor.claude import load_cached_record, save_cached_record

    if use_local_key is None:
        use_local_key = get_anthropic_api_key_optional() is not None

    if use_local_key:
        return extract_all_local(emails, use_cache=use_cache, verbose=verbose)

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
    import time

    with httpx.Client(timeout=120.0) as client:
        for batch_index in range(0, len(pending), BATCH_SIZE):
            batch = pending[batch_index : batch_index + BATCH_SIZE]
            batch_num = batch_index // BATCH_SIZE + 1

            if verbose:
                print(f"Extracting batch {batch_num}/{total_batches} via Fern API ({len(batch)} emails)")

            batch_records = extract_batch_api(batch, client=client)
            for record in batch_records:
                if use_cache:
                    save_cached_record(record)
                records.append(record)

            if batch_index + BATCH_SIZE < len(pending):
                time.sleep(BATCH_SLEEP_SECONDS)

    return records
