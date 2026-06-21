from __future__ import annotations

from typing import Iterator

from fern.gmail.parse import ParsedEmail, parse_message

QUERY_TEMPLATES = [
    '"free trial" OR "your trial" OR "trial ends"',
    '"subscription confirmed" OR "you\'re subscribed" OR "subscription receipt"',
    '"renewal" OR "auto-renews" OR "next billing date"',
    '"receipt" OR "invoice"',
]


def build_search_queries(months: int = 6) -> list[str]:
    days = months * 30
    prefix = f"newer_than:{days}d"
    return [f"{prefix} ({template})" for template in QUERY_TEMPLATES]


def list_message_ids(service, query: str, limit: int | None = None) -> list[str]:
    ids: list[str] = []
    page_token = None

    while True:
        remaining = None if limit is None else limit - len(ids)
        if remaining is not None and remaining <= 0:
            break

        max_results = 500 if remaining is None else min(500, remaining)
        response = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results, pageToken=page_token)
            .execute()
        )

        for item in response.get("messages", []):
            ids.append(item["id"])
            if limit is not None and len(ids) >= limit:
                return ids

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return ids


def list_merged_message_ids(
    service,
    months: int = 6,
    limit: int | None = None,
) -> list[str]:
    """Run all search queries and merge results by message ID (deduplicated)."""
    seen: dict[str, None] = {}

    for query in build_search_queries(months):
        for message_id in list_message_ids(service, query):
            if message_id not in seen:
                seen[message_id] = None
                if limit is not None and len(seen) >= limit:
                    return list(seen.keys())

    return list(seen.keys())


def fetch_message(service, message_id: str) -> dict:
    return (
        service.users()
        .messages()
        .get(userId="me", id=message_id, format="full")
        .execute()
    )


def fetch_parsed_emails(
    service,
    months: int = 6,
    limit: int | None = None,
    message_ids: list[str] | None = None,
) -> Iterator[ParsedEmail]:
    ids = message_ids
    if ids is None:
        ids = list_merged_message_ids(service, months=months, limit=limit)
    elif limit is not None:
        ids = ids[:limit]

    for message_id in ids:
        raw = fetch_message(service, message_id)
        yield parse_message(raw)
