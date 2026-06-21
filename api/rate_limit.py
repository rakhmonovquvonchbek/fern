from __future__ import annotations

import hashlib
import os
from datetime import date

FREE_AUDIT_LIMIT = 3
IP_DAILY_LIMIT = 10
INSTALLS_COLLECTION = "installs"
IPS_COLLECTION = "ips"

_db = None
_install_store: dict[str, dict] = {}
_ip_store: dict[str, dict] = {}


def _use_memory() -> bool:
    return os.environ.get("FERN_LOCAL_RATE_LIMIT") == "memory"


def _client():
    global _db
    if _db is None:
        from google.cloud import firestore

        project = os.environ.get("GCP_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT")
        _db = firestore.Client(project=project)
    return _db


def _today() -> str:
    return date.today().isoformat()


def _ip_doc_id(ip: str) -> str:
    return hashlib.sha256(ip.encode("utf-8")).hexdigest()[:32]


def _get_install_data(install_id: str) -> dict:
    if _use_memory():
        return _install_store.get(install_id, {"total_audits": 0, "last_audit_date": None})

    doc_ref = _client().collection(INSTALLS_COLLECTION).document(install_id)
    snap = doc_ref.get()
    return snap.to_dict() if snap.exists else {"total_audits": 0, "last_audit_date": None}


def _get_ip_data(ip: str) -> dict:
    if _use_memory():
        return _ip_store.get(ip, {"request_count": 0, "last_request_date": None})

    doc_ref = _client().collection(IPS_COLLECTION).document(_ip_doc_id(ip))
    snap = doc_ref.get()
    return snap.to_dict() if snap.exists else {"request_count": 0, "last_request_date": None}


def check_ip_rate_limit(ip: str) -> tuple[bool, str | None, str | None]:
    data = _get_ip_data(ip)
    last_date = data.get("last_request_date")
    count = int(data.get("request_count", 0))

    if last_date != _today():
        return True, None, None

    if count >= IP_DAILY_LIMIT:
        return False, "ip_limit_reached", (
            "Too many requests from this network today (10/day limit). "
            "Try again tomorrow or add ANTHROPIC_API_KEY to ~/.fern/.env for unlimited local audits."
        )

    return True, None, None


def check_rate_limit(install_id: str) -> tuple[bool, str | None, str | None]:
    data = _get_install_data(install_id)
    total = int(data.get("total_audits", 0))
    last_date = data.get("last_audit_date")

    if total >= FREE_AUDIT_LIMIT:
        return False, "free_limit_reached", (
            "You've used your 3 free Fern audits. Add your own Anthropic API key "
            "to ~/.fern/.env to continue unlimited: ANTHROPIC_API_KEY=sk-ant-... "
            "(get one free at console.anthropic.com)"
        )

    if last_date == _today():
        return False, "daily_limit_reached", (
            "You've reached the 1 audit per day limit on the free tier. "
            "Add ANTHROPIC_API_KEY to ~/.fern/.env for unlimited audits, or try again tomorrow."
        )

    return True, None, None


def record_ip_request(ip: str) -> None:
    data = _get_ip_data(ip)
    today = _today()
    if data.get("last_request_date") == today:
        count = int(data.get("request_count", 0)) + 1
    else:
        count = 1

    updated = {"request_count": count, "last_request_date": today}

    if _use_memory():
        _ip_store[ip] = updated
        return

    doc_ref = _client().collection(IPS_COLLECTION).document(_ip_doc_id(ip))
    doc_ref.set(updated, merge=True)


def record_audit(install_id: str) -> None:
    data = _get_install_data(install_id)
    total = int(data.get("total_audits", 0)) + 1
    updated = {"total_audits": total, "last_audit_date": _today()}

    if _use_memory():
        _install_store[install_id] = updated
        return

    doc_ref = _client().collection(INSTALLS_COLLECTION).document(install_id)
    doc_ref.set(updated, merge=True)


def get_client_ip(request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"
