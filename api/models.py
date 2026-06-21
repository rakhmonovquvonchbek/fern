from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class EmailInput(BaseModel):
    message_id: str
    subject: str
    sender: str
    date: str
    body: str


class ExtractRequest(BaseModel):
    emails: list[EmailInput] = Field(min_length=1)


class SubscriptionRecordOut(BaseModel):
    service_name: str
    type: Literal["trial", "subscription", "unclear"]
    amount: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    status: Literal["active", "expired", "cancelled", "unclear"]
    cancel_email: str | None = None
    cancel_url: str | None = None
    source_message_id: str
    source_date: str
    confidence: float


class ExtractResponse(BaseModel):
    records: list[SubscriptionRecordOut]


class PingRequest(BaseModel):
    install_id: str
    os: str
    audit_count: int


class ErrorResponse(BaseModel):
    error: str
    message: str
