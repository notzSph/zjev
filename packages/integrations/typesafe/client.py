#!/usr/bin/env python3
"""Small JSON-in/JSON-out bridge for TypeSafe's Jev System One API."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import urlsplit, urlunsplit
from packages.core.contracts import InputError, validate_request

DEFAULT_BASE_URL = "https://api.typesafe.ai"


def _base_url(url: str | None) -> str:
    configured = url or os.environ.get("TYPESAFE_API_BASE_URL")
    if configured:
        return configured.rstrip("/")
    endpoint = os.environ.get("TYPESAFE_API_URL")
    if endpoint:
        parsed = urlsplit(endpoint)
        return urlunsplit((parsed.scheme, parsed.netloc, "", "", "")).rstrip("/")
    return DEFAULT_BASE_URL


def _sdk_questions(questions: dict[str, Any]) -> dict[str, Any]:
    from typesafe_sdk import Choice, Noul, Score

    built = {}
    for question_id, question in questions.items():
        common = {"instructions": question["instructions"]}
        if question["type"] == "choice":
            built[question_id] = Choice(criteria=question["criteria"], **common)
        elif question["type"] == "score":
            built[question_id] = Score(criteria=question["criteria"], **common)
        else:
            built[question_id] = Noul(criteria=question.get("criteria"), **common)
    return built


def evaluate(payload: Any, *, api_key: str | None = None, url: str | None = None,
             timeout: float = 30.0, retries: int = 3) -> dict[str, Any]:
    request_body = validate_request(payload)
    key = (api_key or os.environ.get("TYPESAFE_API_KEY")
           or os.environ.get("JEV_API_KEY"))
    if not key:
        raise RuntimeError("TYPESAFE_API_KEY or JEV_API_KEY is not set")
    try:
        from typesafe_sdk import TypeSafeClient
        response = TypeSafeClient(
            api_key=key,
            model=request_body["model"],
            timeout=timeout,
            base_url=_base_url(url),
        ).system_one(
            state=request_body["state"],
            questions=_sdk_questions(request_body["questions"]),
            model=request_body["model"],
        )
        return response.model_dump(mode="json")
    except ImportError as error:
        raise RuntimeError("typesafe-sdk is not installed; install infra/requirements.txt") from error
