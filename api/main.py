from __future__ import annotations

import logging

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from extract import extract_records
from models import ErrorResponse, ExtractRequest, ExtractResponse, PingRequest, SubscriptionRecordOut
from rate_limit import (
    check_ip_rate_limit,
    check_rate_limit,
    get_client_ip,
    record_audit,
    record_ip_request,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fern-api")

REQUIRED_USER_AGENT = "Fern/0.2"

app = FastAPI(title="Fern API", version="0.2.0")


def _validate_client(user_agent: str | None, install_id: str | None) -> None:
    if user_agent != REQUIRED_USER_AGENT:
        raise HTTPException(status_code=403, detail="Invalid client")
    if not install_id:
        raise HTTPException(status_code=400, detail="Missing X-Fern-Install-ID header")


@app.post("/extract", response_model=ExtractResponse)
def extract_endpoint(
    request: Request,
    body: ExtractRequest,
    user_agent: str | None = Header(default=None, alias="User-Agent"),
    install_id: str | None = Header(default=None, alias="X-Fern-Install-ID"),
):
    _validate_client(user_agent, install_id)

    client_ip = get_client_ip(request)
    allowed, error_code, message = check_ip_rate_limit(client_ip)
    if not allowed:
        return JSONResponse(
            status_code=429,
            content=ErrorResponse(error=error_code or "ip_limit_reached", message=message or "").model_dump(),
        )

    allowed, error_code, message = check_rate_limit(install_id)
    if not allowed:
        return JSONResponse(
            status_code=429,
            content=ErrorResponse(error=error_code or "free_limit_reached", message=message or "").model_dump(),
        )

    emails = [e.model_dump() for e in body.emails]
    records = extract_records(emails)
    record_audit(install_id)
    record_ip_request(client_ip)

    return ExtractResponse(records=[SubscriptionRecordOut(**r) for r in records])


@app.post("/ping")
def ping_endpoint(
    body: PingRequest,
    user_agent: str | None = Header(default=None, alias="User-Agent"),
    install_id: str | None = Header(default=None, alias="X-Fern-Install-ID"),
):
    _validate_client(user_agent, install_id)
    if body.install_id != install_id:
        raise HTTPException(status_code=400, detail="install_id mismatch")

    logger.info(
        "telemetry ping install_id=%s os=%s audit_count=%s",
        body.install_id,
        body.os,
        body.audit_count,
    )
    return {"ok": True}


@app.get("/health")
def health():
    return {"status": "ok"}
