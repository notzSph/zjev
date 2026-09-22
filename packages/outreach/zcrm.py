"""Scoped zCRM adapter for importing reviewed outreach targets."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from .ratelimit import OutboundRateLimiter


class ZCRMNotConfigured(RuntimeError):
    pass


class ZCRMRequestError(RuntimeError):
    pass


@dataclass(frozen=True)
class ZCRMClient:
    base_url: str
    api_token: str
    business_id: str
    opener: Callable[..., Any] = urllib.request.urlopen
    limiter: OutboundRateLimiter | None = None

    @classmethod
    def from_env(cls, opener: Callable[..., Any] = urllib.request.urlopen) -> "ZCRMClient":
        values = {
            "base_url": os.environ.get("ZCRM_API_URL", "").strip(),
            "api_token": os.environ.get("ZCRM_API_TOKEN", "").strip(),
            "business_id": os.environ.get("ZCRM_BUSINESS_ID", "").strip(),
        }
        if not all(values.values()):
            raise ZCRMNotConfigured(
                "zCRM requires ZCRM_API_URL, ZCRM_API_TOKEN, and ZCRM_BUSINESS_ID"
            )
        return cls(opener=opener, **values)

    def upsert_leads(self, leads: list[dict[str, Any]]) -> dict[str, Any]:
        if not leads:
            raise ValueError("leads must not be empty")
        if self.limiter is not None:
            self.limiter.acquire("zcrm")
        request = urllib.request.Request(
            f"{self.base_url.rstrip('/')}/api/v1/agent/outreach/leads",
            data=json.dumps({"leads": leads}).encode(),
            headers={
                "Content-Type": "application/json",
                "X-API-Key": self.api_token,
                "X-Business-ID": self.business_id,
            },
            method="PUT",
        )
        try:
            with self.opener(request, timeout=15) as response:
                body = json.loads(response.read())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            raise ZCRMRequestError("zCRM lead upsert failed") from error
        if not isinstance(body, dict) or not isinstance(body.get("leads"), list):
            raise ZCRMRequestError("zCRM returned an invalid lead upsert response")
        return body


def score_to_zcrm_lead(score: dict[str, Any]) -> dict[str, Any]:
    candidate = score.get("candidate") or score.get("target") or {}
    if not isinstance(candidate, dict):
        raise ValueError("score candidate must be an object")
    candidate_id = candidate.get("candidate_id") or score.get("candidate_id")
    company = candidate.get("company_name")
    if not isinstance(candidate_id, str) or not candidate_id.strip():
        raise ValueError("score candidate_id must be a non-empty string")
    if not isinstance(company, str) or not company.strip():
        raise ValueError("score company_name must be a non-empty string")
    evidence = score.get("evidence_packet", {})
    policy = score.get("policy", {})
    return {
        "company": company.strip(),
        "contact_name": None,
        "source": "jevzoo",
        "tags": ["jevzoo", "outreach", "business_target"],
        "external_ref": candidate_id.strip(),
        "status": "target",
        "description": json.dumps(
            {
                "geography": candidate.get("geography"),
                "target_profile": candidate.get("target_profile"),
                "rank_score": score.get("rank_score"),
                "eligible": score.get("eligible", False),
                "policy": policy,
                "evidence_packet": evidence,
            },
            sort_keys=True,
        ),
        "next_action": "Review Jevzoo outreach score",
    }


def export_scores_to_zcrm(
    scores: list[dict[str, Any]],
    client: ZCRMClient,
    *,
    include_ineligible: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    selected = [score for score in scores if include_ineligible or score.get("eligible") is True]
    leads = [score_to_zcrm_lead(score) for score in selected]
    result: dict[str, Any] = {
        "count": len(leads),
        "skipped": len(scores) - len(leads),
        "dry_run": dry_run,
        "leads": leads,
    }
    if not dry_run and leads:
        result["zcrm"] = client.upsert_leads(leads)
    return result
