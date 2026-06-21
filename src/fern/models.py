from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal


RecordType = Literal["trial", "subscription", "unclear"]
RecordStatus = Literal["active", "expired", "cancelled", "unclear"]


@dataclass
class SubscriptionRecord:
    service_name: str
    type: RecordType
    amount: str | None
    start_date: str | None
    end_date: str | None
    status: RecordStatus
    cancel_email: str | None
    cancel_url: str | None
    source_message_id: str
    source_date: str
    confidence: float

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> SubscriptionRecord:
        return cls(
            service_name=str(data.get("service_name", "Unknown")),
            type=data.get("type", "unclear"),
            amount=data.get("amount"),
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
            status=data.get("status", "unclear"),
            cancel_email=data.get("cancel_email"),
            cancel_url=data.get("cancel_url"),
            source_message_id=str(data.get("source_message_id", "")),
            source_date=str(data.get("source_date", "")),
            confidence=float(data.get("confidence", 0.0)),
        )
