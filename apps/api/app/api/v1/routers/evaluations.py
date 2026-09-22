from __future__ import annotations

from fastapi import APIRouter

from packages.integrations.typesafe import evaluate
from packages.job_fit import build_job_fit_request, derive_job_fit_policy

from ...deps import AuthDependency
from ..schemas.evaluations import GenericEvaluateRequest, JobFitRequest

router = APIRouter(prefix="/v1", tags=["evaluations"])


@router.post("/evaluate")
def generic_evaluate(payload: GenericEvaluateRequest, _: AuthDependency) -> dict[str, Any]:
    return evaluate(payload.model_dump())


@router.post("/job_fit")
def job_fit(payload: JobFitRequest, _: AuthDependency) -> dict[str, Any]:
    result = evaluate(build_job_fit_request(payload.cv, payload.job_description, payload.model))
    result["policy"] = derive_job_fit_policy(result)
    return result
