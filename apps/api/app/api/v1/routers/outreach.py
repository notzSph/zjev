from __future__ import annotations

import os
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, status

from packages.integrations.typesafe import evaluate
from packages.outreach import (
    build_outreach_request,
    build_target_selection_plan,
    derive_outreach_policy,
    import_target_csv,
    rank_scores,
    ranked_csv,
    score_target_batch,
    process_job,
    search_google_places,
    source_status,
    validate_target_batch,
    ZCRMClient,
    export_scores_to_zcrm,
)

from ...deps import AuthDependency, get_audit_store
from ....services.outreach import score_batch
from ..schemas.outreach import (
    CalibrationRequest,
    GooglePlacesRequest,
    GooglePlacesScoreRequest,
    OutcomeRequest,
    OutreachEvaluateRequest,
    RankRequest,
    ScoreBatchRequest,
    ScoreJobRequest,
    TargetBatchRequest,
    TargetImportRequest,
    TargetPlanRequest,
    ZCRMExportRequest,
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


@router.post("/zcrm/export")
def export_zcrm(payload: ZCRMExportRequest, _: AuthDependency) -> dict[str, Any]:
    client = ZCRMClient.from_env()
    return export_scores_to_zcrm(
        payload.scores,
        client,
        include_ineligible=payload.include_ineligible,
        dry_run=payload.dry_run,
    )


@router.post("/sources/google-places")
def google_places(payload: GooglePlacesRequest, _: AuthDependency) -> dict[str, Any]:
    leads = search_google_places(
        os.environ.get("GOOGLE_MAPS_API_KEY"), payload.query, max_results=payload.max_results
    )
    return {"count": len(leads), "leads": leads, "discovery_only": True, "requires_manual_enrichment": True}


@router.post("/sources/google-places/score")
def score_google_businesses(
    payload: GooglePlacesScoreRequest, _: AuthDependency, store: AuditStore
) -> dict[str, Any]:
    leads = search_google_places(
        os.environ.get("GOOGLE_MAPS_API_KEY"), payload.query, max_results=payload.max_results
    )
    run_id = payload.run_id or str(uuid.uuid4())
    cached = store.get_run(run_id)
    if cached is not None:
        return {**cached, "idempotent_replay": True}
    candidates = validate_target_batch(leads)
    store.create_run(run_id)
    scores = score_target_batch(
        candidates, payload.offer, payload.proof_assets, evaluate, store, run_id
    )
    ranked = rank_scores(scores)
    result = {
        "run_id": run_id,
        "count": len(ranked),
        "scores": ranked,
        "csv": ranked_csv(ranked),
        "entity_type": "business",
        "stops_at_account_scoring": True,
        "idempotent_replay": False,
    }
    store.save_run(run_id, result)
    return result


@router.post("/score")
def score(payload: ScoreBatchRequest, _: AuthDependency, store: AuditStore) -> dict[str, Any]:
    run_id = payload.run_id or str(uuid.uuid4())
    return score_batch({**payload.model_dump(), "run_id": run_id}, store)


@router.post("/score/jobs", status_code=status.HTTP_202_ACCEPTED)
def enqueue_score_job(
    payload: ScoreJobRequest,
    background_tasks: BackgroundTasks,
    _: AuthDependency,
    store: AuditStore,
) -> dict[str, Any]:
    job_id = payload.run_id or str(uuid.uuid4())
    job_payload = {**payload.model_dump(), "run_id": job_id}
    job = store.enqueue_job(job_id, job_payload, payload.max_attempts)
    if job["status"] == "queued":
        background_tasks.add_task(
            process_job,
            store,
            job_id,
            lambda data: score_batch(data, store),
        )
    return {
        "job_id": job_id,
        "status": job["status"],
        "attempts": job["attempts"],
        "max_attempts": job["max_attempts"],
        "idempotent_replay": job["attempts"] > 0 or job["status"] != "queued",
    }


@router.get("/score/jobs/{job_id}")
def get_score_job(job_id: str, _: AuthDependency, store: AuditStore) -> dict[str, Any]:
    job = store.get_job(job_id)
    if job is None:
        raise ValueError("job_id was not found")
    return job


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
