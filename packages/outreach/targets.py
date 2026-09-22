"""Validate candidate batches before evaluation or persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

MAX_CANDIDATES = 25
MAX_EVIDENCE_ITEMS = 20


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _optional_text(value: Any, name: str) -> str | None:
    if value is None:
        return None
    return _text(value, name)


def _url(value: Any, name: str) -> str:
    result = _text(value, name)
    parsed = urlparse(result)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{name} must be an http(s) URL")
    return result


def _timestamp(value: Any, name: str) -> str:
    result = _text(value, name)
    try:
        parsed = datetime.fromisoformat(result.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{name} must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None:
        raise ValueError(f"{name} must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat()


def _source_records(value: Any, urls: list[str], name: str) -> list[dict[str, Any]]:
    if value is None:
        return [{"url": url, "captured_at": None, "source_type": "unknown"} for url in urls]
    if not isinstance(value, list) or len(value) > MAX_EVIDENCE_ITEMS:
        raise ValueError(f"{name} must be a list of up to {MAX_EVIDENCE_ITEMS} objects")
    records = []
    seen = set()
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"{name} item {index} must be an object")
        url = _url(item.get("url"), f"{name} item {index} url")
        if url in seen:
            continue
        seen.add(url)
        captured_at = item.get("captured_at")
        records.append({
            "url": url,
            "captured_at": _timestamp(captured_at, f"{name} item {index} captured_at")
            if captured_at is not None else None,
            "source_type": _text(item.get("source_type", "unknown"), f"{name} item {index} source_type"),
        })
    return records


def _evidence(value: Any, name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > MAX_EVIDENCE_ITEMS:
        raise ValueError(f"{name} must be a list of up to {MAX_EVIDENCE_ITEMS} strings")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{name} must contain non-empty strings")
    return [item.strip() for item in value]


def validate_target_candidate(candidate: Any, index: int = 0) -> dict[str, Any]:
    if not isinstance(candidate, dict):
        raise ValueError(f"candidate {index} must be an object")
    source_urls = candidate.get("source_urls")
    if not isinstance(source_urls, list) or not source_urls:
        raise ValueError(f"candidate {index} needs at least one source_urls entry")
    normalized_urls = [_url(item, f"candidate {index} source_urls") for item in source_urls]
    normalized_urls = list(dict.fromkeys(normalized_urls))
    return {
        "candidate_id": _text(candidate.get("candidate_id"), f"candidate {index} candidate_id"),
        "person_name": _optional_text(candidate.get("person_name"), f"candidate {index} person_name"),
        "company_name": _text(candidate.get("company_name"), f"candidate {index} company_name"),
        "role": _text(candidate.get("role"), f"candidate {index} role"),
        "geography": _text(candidate.get("geography"), f"candidate {index} geography"),
        "target_profile": _text(candidate.get("target_profile"), f"candidate {index} target_profile"),
        "linkedin_activity": _text(candidate.get("linkedin_activity"), f"candidate {index} linkedin_activity"),
        "prior_interactions": _optional_text(
            candidate.get("prior_interactions"), f"candidate {index} prior_interactions"
        ),
        "evidence": _evidence(candidate.get("evidence"), f"candidate {index} evidence"),
        "source_urls": normalized_urls,
        "source_records": _source_records(
            candidate.get("source_records"), normalized_urls, f"candidate {index} source_records"
        ),
    }


def validate_target_batch(candidates: Any) -> list[dict[str, Any]]:
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("candidates must be a non-empty list")
    if len(candidates) > MAX_CANDIDATES:
        raise ValueError(f"candidates cannot exceed {MAX_CANDIDATES} items")
    normalized = [validate_target_candidate(candidate, index) for index, candidate in enumerate(candidates)]
    ids = [candidate["candidate_id"] for candidate in normalized]
    if len(ids) != len(set(ids)):
        raise ValueError("candidate_id values must be unique within a batch")
    return normalized
