"""Build conservative, human-executed target discovery plans."""

from __future__ import annotations

import re
from typing import Any

from .calibration import DISQUALIFIERS, ICP, OFFER_LANES, Z_CALIBRATION_VERSION

MAX_QUERY_TERMS = 8


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _terms(value: Any, name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ValueError(f"{name} must contain non-empty strings")
    cleaned = []
    for item in value:
        term = re.sub(r"\s+", " ", item.strip())
        if term and term not in cleaned:
            cleaned.append(term)
    return cleaned[:MAX_QUERY_TERMS]


def build_target_selection_plan(
    offer: str,
    geography: str | None = None,
    company_terms: list[str] | None = None,
    buyer_titles: list[str] | None = None,
    priority_signals: list[str] | None = None,
) -> dict[str, Any]:
    """Return a search brief, not a scrape or an automated outreach action."""
    offer_text = _text(offer, "offer")
    if geography is not None and not isinstance(geography, str):
        raise ValueError("geography must be a non-empty string")
    geography_text = geography.strip() if geography is not None else ICP["geography"][0]
    if not geography_text:
        raise ValueError("geography must be a non-empty string")
    companies = _terms(company_terms, "company_terms") or [ICP["company_profile"]]
    titles = _terms(buyer_titles, "buyer_titles") or list(ICP["buyer_titles"])
    signals = _terms(priority_signals, "priority_signals") or list(ICP["priority_signals"])
    query_terms = [offer_text, geography_text, *titles[:3], *signals[:3]]
    query = " ".join(f'"{term}"' if " " in term else term for term in query_terms)
    return {
        "type": "human_target_selection_plan",
        "calibration_version": Z_CALIBRATION_VERSION,
        "search": {
            "query": query,
            "geography": geography_text,
            "company_terms": companies,
            "buyer_titles": titles,
            "priority_signals": signals,
            "offer": offer_text,
        },
        "qualification": {
            "required": [
                "credible fit with the company profile and offer lane",
                "credible buyer or influential stakeholder relevance",
                "one recent, specific trigger or operational signal",
            ],
            "exclude": list(DISQUALIFIERS),
        },
        "workflow": [
            "find a small set of public candidate profiles or company pages",
            "record source URL and evidence before scoring",
            "run each candidate through /v1/outreach/evaluate",
            "manually review and approve any draft before contact",
        ],
        "guardrails": {
            "max_candidates_per_batch": 25,
            "low_volume_manual_research": True,
            "auto_scrape": False,
            "auto_contact": False,
        },
        "offer_lanes": list(OFFER_LANES),
    }
