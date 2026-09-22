from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from packages.integrations.typesafe import evaluate
from packages.job_fit import build_job_fit_request, derive_job_fit_policy

from ...dependencies import AuthDependency
from ..schemas.common import StrictModel

router = APIRouter(prefix="/v1", tags=["evaluations"])


class GenericEvaluateRequest(StrictModel):
    state: str | dict[str, Any] | list[Any]
    questions: dict[str, Any]
    model: str = "jev-latest"


class JobFitRequest(StrictModel):
    cv: Any
    job_description: Any
    model: str = "jev-latest"


@router.post("/evaluate")
def generic_evaluate(payload: GenericEvaluateRequest, _: AuthDependency) -> dict[str, Any]:
    return evaluate(payload.model_dump())


@router.post("/job_fit")
def job_fit(payload: JobFitRequest, _: AuthDependency) -> dict[str, Any]:
    result = evaluate(build_job_fit_request(payload.cv, payload.job_description, payload.model))
    result["policy"] = derive_job_fit_policy(result)
    return result
