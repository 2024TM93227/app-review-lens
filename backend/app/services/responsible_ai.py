"""Responsible AI policy helpers: PII scrubbing, payload minimization, and policy metadata."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import os
import re
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class PIIScrubResult:
    text: str
    entities: Dict[str, int]


_EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)?\d{3}[\s.-]?\d{4}(?!\d)")
_CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
_UPI_RE = re.compile(r"\b[a-zA-Z0-9._-]{2,}@[a-zA-Z]{2,}\b")
_IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_ORDER_ID_RE = re.compile(r"\b(?:order|booking|txn|transaction|ticket)[\s:#-]*[a-zA-Z0-9-]{5,}\b", re.IGNORECASE)


DEFAULT_POLICY = {
    "pii_scrubbing_enabled": True,
    "scrub_email": True,
    "scrub_phone": True,
    "scrub_card": True,
    "scrub_upi": True,
    "scrub_ip": True,
    "scrub_order_id": True,
    "store_raw_payload": False,
    "store_author_name": False,
    "llm_payload_scrub": True,
}


def _env_bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def get_policy_config() -> Dict[str, bool]:
    return {
        "pii_scrubbing_enabled": _env_bool("RAI_PII_SCRUB", DEFAULT_POLICY["pii_scrubbing_enabled"]),
        "scrub_email": _env_bool("RAI_SCRUB_EMAIL", DEFAULT_POLICY["scrub_email"]),
        "scrub_phone": _env_bool("RAI_SCRUB_PHONE", DEFAULT_POLICY["scrub_phone"]),
        "scrub_card": _env_bool("RAI_SCRUB_CARD", DEFAULT_POLICY["scrub_card"]),
        "scrub_upi": _env_bool("RAI_SCRUB_UPI", DEFAULT_POLICY["scrub_upi"]),
        "scrub_ip": _env_bool("RAI_SCRUB_IP", DEFAULT_POLICY["scrub_ip"]),
        "scrub_order_id": _env_bool("RAI_SCRUB_ORDER_ID", DEFAULT_POLICY["scrub_order_id"]),
        "store_raw_payload": _env_bool("RAI_STORE_RAW_PAYLOAD", DEFAULT_POLICY["store_raw_payload"]),
        "store_author_name": _env_bool("RAI_STORE_AUTHOR", DEFAULT_POLICY["store_author_name"]),
        "llm_payload_scrub": _env_bool("RAI_LLM_SCRUB", DEFAULT_POLICY["llm_payload_scrub"]),
    }


def scrub_text_pii(text: str) -> PIIScrubResult:
    cfg = get_policy_config()
    if not cfg["pii_scrubbing_enabled"] or not text:
        return PIIScrubResult(text=text, entities={})

    result = text
    entities: Dict[str, int] = {}

    if cfg["scrub_email"]:
        result, count = _EMAIL_RE.subn("[EMAIL_REDACTED]", result)
        if count:
            entities["email"] = entities.get("email", 0) + count

    if cfg["scrub_phone"]:
        result, count = _PHONE_RE.subn("[PHONE_REDACTED]", result)
        if count:
            entities["phone"] = entities.get("phone", 0) + count

    if cfg["scrub_card"]:
        result, count = _CARD_RE.subn("[CARD_REDACTED]", result)
        if count:
            entities["card"] = entities.get("card", 0) + count

    if cfg["scrub_upi"]:
        result, count = _UPI_RE.subn("[UPI_REDACTED]", result)
        if count:
            entities["upi"] = entities.get("upi", 0) + count

    if cfg["scrub_ip"]:
        result, count = _IP_RE.subn("[IP_REDACTED]", result)
        if count:
            entities["ip"] = entities.get("ip", 0) + count

    if cfg["scrub_order_id"]:
        result, count = _ORDER_ID_RE.subn("[ORDER_ID_REDACTED]", result)
        if count:
            entities["order_id"] = entities.get("order_id", 0) + count

    return PIIScrubResult(text=result, entities=entities)


def scrub_author(author: str | None) -> str | None:
    cfg = get_policy_config()
    if cfg["store_author_name"]:
        return author
    if not author:
        return None

    digest = hashlib.sha256(author.encode("utf-8")).hexdigest()[:12]
    return f"user_{digest}"


def scrub_payload_pii(payload: Any) -> Tuple[Any, Dict[str, int]]:
    """Recursively scrub text-like values in nested payloads."""
    totals: Dict[str, int] = {}

    def _walk(value: Any) -> Any:
        if isinstance(value, str):
            scrubbed = scrub_text_pii(value)
            for k, v in scrubbed.entities.items():
                totals[k] = totals.get(k, 0) + v
            return scrubbed.text
        if isinstance(value, list):
            return [_walk(v) for v in value]
        if isinstance(value, tuple):
            return tuple(_walk(v) for v in value)
        if isinstance(value, dict):
            return {k: _walk(v) for k, v in value.items()}
        return value

    return _walk(deepcopy(payload)), totals


def maybe_store_raw_payload(payload: Dict[str, Any]) -> Dict[str, Any] | None:
    cfg = get_policy_config()
    if not cfg["store_raw_payload"]:
        return None
    scrubbed, _ = scrub_payload_pii(payload)
    return scrubbed


def sanitize_llm_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    cfg = get_policy_config()
    if not cfg["llm_payload_scrub"]:
        return payload
    scrubbed, _ = scrub_payload_pii(payload)
    return scrubbed


def policy_manifest() -> Dict[str, Any]:
    cfg = get_policy_config()
    return {
        "name": "Responsible AI Baseline Policy",
        "version": "1.0",
        "controls": {
            "pii_scrubbing": cfg["pii_scrubbing_enabled"],
            "llm_payload_scrubbing": cfg["llm_payload_scrub"],
            "raw_payload_storage": cfg["store_raw_payload"],
            "author_pseudonymization": not cfg["store_author_name"],
        },
        "notes": [
            "PII entities are redacted from review text and model payloads by default.",
            "Raw provider payloads are disabled by default to reduce PII retention.",
            "Reviewer names are pseudonymized unless explicitly enabled.",
            "Additional governance (bias audits, human review gates) should be layered on top for production use.",
        ],
    }
