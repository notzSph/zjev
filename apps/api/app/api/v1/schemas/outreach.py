from __future__ import annotations

from typing import Any

from .common import StrictModel


class OutreachEvaluateRequest(StrictModel):
    target_profile: str
    linkedin_activity: str
    offer: str
    proof_assets: list[str]
    prior_interactions: str | None = None
    model: str = "jev-latest"


class TargetPlanRequest(StrictModel):
    offer: str
    geography: str | None = None
    company_terms: list[str] | None = None
    buyer_titles: list[str] | None = None
    priority_signals: list[str] | None = None


class TargetBatchRequest(StrictModel):
    candidates: list[dict[str, Any]]


class TargetImportRequest(StrictModel):
    csv: str


class ScoreBatchRequest(StrictModel):
    offer: str
    proof_assets: list[str]
    candidates: list[dict[str, Any]]
    run_id: str | None = None


class ScoreJobRequest(ScoreBatchRequest):
    max_attempts: int = 3


class RankRequest(StrictModel):
    scores: list[dict[str, Any]]


class OutcomeRequest(StrictModel):
    audit_id: int
    outcome: str
    note: str | None = None


class CalibrationRequest(StrictModel):
    minimum_labeled: int = 30


class GooglePlacesRequest(StrictModel):
    query: str
    max_results: int = 20


class GooglePlacesScoreRequest(StrictModel):
    query: str
    offer: str
    proof_assets: list[str]
    max_results: int = 20
    run_id: str | None = None
