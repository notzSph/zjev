from __future__ import annotations

import os
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends

from packages.integrations.typesafe import evaluate
from packages.outreach import (
    build_outreach_request,
    build_target_selection_plan,
    derive_outreach_policy,
    import_target_csv,
    rank_scores,
    ranked_csv,
    score_target_batch,
    search_google_places,
    source_status,
    validate_target_batch,
)

from ...dependencies import AuthDependency, get_audit_store
from ..schemas.outreach import (
    CalibrationRequest,
    GooglePlacesRequest,
    OutcomeRequest,
    OutreachEvaluateRequest,
    RankRequest,
    ScoreBatchRequest,
    TargetBatchRequest,
    TargetImportRequest,
    TargetPlanRequest,
)

router = APIRouter(prefix="/v1/outreach", tags=["outreach"])
AuditStore = Annotated[Any, Depends(get_audit_store)]


@router.post("/evaluate")
def evaluate_outreach(payload: OutreachEvaluateRequest, _: AuthDependency) -> dict[str, Any]:
    result = evaluate(build_outreach_request(**payload.model_dump()))
    result["policy"] = derive_outreach_policy(result)
    return result


@router.post("/target-plan")
def target_plan(payload: TargetPlanRequest, _: AuthDependency) -> dict[str, Any]:
    return build_target_selection_plan(**payload.model_dump())


@router.post("/targets/validate")
def validate_targets(payload: TargetBatchRequest, _: AuthDependency) -> dict[str, Any]:
    candidates = validate_target_batch(payload.candidates)
    return {"count": len(candidates), "candidates": candidates, "ready_for_scoring": True}


@router.post("/targets/import")
def import_targets(payload: TargetImportRequest, _: AuthDependency) -> dict[str, Any]:
    candidates = import_target_csv(payload.csv)
    return {"count": len(candidates), "candidates": candidates, "ready_for_scoring": True}


@router.post("/sources/status")
def sources(_: AuthDependency) -> dict[str, Any]:
    return source_status()


@router.post("/sources/google-places")
def google_places(payload: GooglePlacesRequest, _: AuthDependency) -> dict[str, Any]:
    leads = search_google_places(
        os.environ.get("GOOGLE_MAPS_API_KEY"), payload.query, max_results=payload.max_results
    )
    return {"count": len(leads), "leads": leads, "discovery_only": True, "requires_manual_enrichment": True}


@router.post("/score")
def score(payload: ScoreBatchRequest, _: AuthDependency, store: AuditStore) -> dict[str, Any]:
    candidates = validate_target_batch(payload.candidates)
    run_id = payload.run_id or str(uuid.uuid4())
    cached = store.get_run(run_id)
    if cached is not None:
        return {**cached, "idempotent_replay": True}
    scores = score_target_batch(
        candidates, payload.offer, payload.proof_assets, evaluate, store, run_id
    )
    ranked = rank_scores(scores)
    result = {"run_id": run_id, "count": len(ranked), "scores": ranked, "csv": ranked_csv(ranked), "idempotent_replay": False}
    store.save_run(run_id, result)
    return result


@router.post("/rank")
def rank(payload: RankRequest, _: AuthDependency) -> dict[str, Any]:
    ranked = rank_scores(payload.scores)
    return {"count": len(ranked), "scores": ranked, "csv": ranked_csv(ranked)}


@router.post("/outcomes")
def outcome(payload: OutcomeRequest, _: AuthDependency, store: AuditStore) -> dict[str, bool]:
    store.record_outcome(payload.audit_id, payload.outcome, payload.note)
    return {"updated": True}


@router.post("/metrics")
def metrics(_: AuthDependency, store: AuditStore) -> dict[str, Any]:
    return store.metrics()


@router.post("/calibration")
def calibration(payload: CalibrationRequest, _: AuthDependency, store: AuditStore) -> dict[str, Any]:
    return store.calibration_report(payload.minimum_labeled)
