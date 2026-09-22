"""Deterministic ranking for already-scored outreach candidates."""

from __future__ import annotations

import csv
import io
from typing import Any

WEIGHTS = {
    "icp_fit": 0.25,
    "buyer_relevance": 0.20,
    "buying_signal": 0.20,
    "personalization_evidence": 0.15,
    "generic_risk": -0.10,
    "account_safety_risk": -0.10,
}


def _signal(result: dict[str, Any], name: str) -> float:
    value = result.get("policy", {}).get("signals", {}).get(name)
    return float(value) if isinstance(value, (int, float)) else 0.0


def _rank_score(result: dict[str, Any]) -> float:
    raw = sum(weight * _signal(result, name) for name, weight in WEIGHTS.items())
    return round(max(0.0, min(100.0, raw / 4.0 * 100.0)), 3)


def rank_scores(scores: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(scores, list):
        raise ValueError("scores must be a list")
    ranked = []
    for item in scores:
        if not isinstance(item, dict) or not isinstance(item.get("policy"), dict):
            raise ValueError("each score must contain a policy object")
        policy = item["policy"]
        enriched = dict(item)
        enriched["rank_score"] = _rank_score(item)
        evidence = item.get("evidence_packet", {})
        has_evidence = bool(evidence.get("items")) if isinstance(evidence, dict) else True
        is_stale = isinstance(evidence, dict) and evidence.get("freshness_status") == "stale"
        citations_complete = (
            isinstance(evidence, dict) and evidence.get("citation_status") == "complete"
        )
        no_contradictions = (
            isinstance(evidence, dict) and evidence.get("contradiction_status") != "review"
        )
        enriched["eligible"] = (
            policy.get("recommended_action") in {"draft_for_review", "human_review"}
            and has_evidence
            and not is_stale
            and citations_complete
            and no_contradictions
            and policy.get("abstained") is not True
        )
        ranked.append(enriched)
    ranked.sort(
        key=lambda item: (
            item["eligible"], item["rank_score"],
            item["policy"].get("confidence_floor") or 0.0,
            item.get("candidate_id", ""),
        ),
        reverse=True,
    )
    for position, item in enumerate(ranked, start=1):
        item["rank"] = position
    return ranked


def ranked_csv(scores: list[dict[str, Any]]) -> str:
    fields = ["rank", "candidate_id", "rank_score", "eligible", "recommended_action", "confidence_band"]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for item in scores:
        policy = item["policy"]
        writer.writerow({
            "rank": item["rank"],
            "candidate_id": item.get("candidate_id", ""),
            "rank_score": item["rank_score"],
            "eligible": item["eligible"],
            "recommended_action": policy.get("recommended_action", ""),
            "confidence_band": policy.get("confidence_band", ""),
        })
    return output.getvalue()
