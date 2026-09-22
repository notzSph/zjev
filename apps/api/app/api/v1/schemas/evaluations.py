from __future__ import annotations

from typing import Any

from .common import StrictModel


class GenericEvaluateRequest(StrictModel):
    state: str | dict[str, Any] | list[Any]
    questions: dict[str, Any]
    model: str = "jev-latest"


class JobFitRequest(StrictModel):
    cv: Any
    job_description: Any
    model: str = "jev-latest"
